"""Pipeline orchestrator -- wires poll, filter, triage, save, and label.

This is the ONLY service module that imports Django ORM. Per locked
decision: "GmailPoller returns EmailMessage, a save step maps it to
the Email model."

Flow: poll -> dedup -> spam filter -> AI triage -> save to DB -> label Gmail
Safety: label-after-persist (Gmail label only applied after DB write succeeds)
"""

import logging
from datetime import timedelta
from typing import Optional

from django.db import close_old_connections

from django.db import models as db_models

from apps.core.models import SystemConfig
from apps.emails.models import ActivityLog, AttachmentMetadata, Email, Thread
from apps.emails.services.ai_processor import AIProcessor
from apps.emails.services.assignment import update_thread_preview
from apps.emails.services.dtos import EmailMessage, TriageResult
from apps.emails.services.sla import set_sla_deadlines
from apps.emails.services.spam_filter import is_spam as spam_filter_fn_default

logger = logging.getLogger(__name__)


def _map_suggested_assignee(triage: TriageResult) -> dict:
    """Map TriageResult suggested_assignee fields to JSONField-compatible dict.

    Prefers suggested_assignee_detail (structured) if available.
    Falls back to suggested_assignee string wrapped in {"name": ...}.
    Tries to match name to a User for user_id.
    Returns empty dict if nothing available.
    """
    detail = getattr(triage, "suggested_assignee_detail", {})
    if not detail and triage.suggested_assignee:
        detail = {"name": triage.suggested_assignee}

    if not detail:
        return {}

    # Try to resolve user_id from name
    if detail.get("name") and "user_id" not in detail:
        try:
            from apps.accounts.models import User
            from django.db.models import Q

            name = detail["name"]
            user = User.objects.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name) | Q(username__icontains=name),
                is_active=True,
            ).first()
            if user:
                detail["user_id"] = user.pk
        except Exception:
            pass  # Non-critical -- user_id is a convenience field

    return detail


def save_email_to_db(email_msg: EmailMessage, triage: TriageResult) -> Email:
    """Create or update an Email record from EmailMessage + TriageResult.

    Uses update_or_create with message_id as lookup key for dedup.
    Also saves AttachmentMetadata for each attachment.
    """
    email_obj, created = Email.objects.update_or_create(
        message_id=email_msg.message_id,
        defaults={
            "gmail_id": email_msg.message_id,
            "gmail_thread_id": email_msg.thread_id,
            "from_address": email_msg.sender_email,
            "from_name": email_msg.sender_name,
            "to_inbox": email_msg.inbox,
            "subject": email_msg.subject,
            "body": email_msg.body,
            "body_html": email_msg.body_html,
            "received_at": email_msg.timestamp,
            "gmail_link": email_msg.gmail_link,
            # AI triage fields
            "category": triage.category,
            "priority": triage.priority,
            "ai_summary": triage.summary,
            "ai_reasoning": triage.reasoning,
            "ai_model_used": triage.model_used,
            "ai_tags": triage.tags,
            "ai_suggested_assignee": _map_suggested_assignee(triage),
            "ai_input_tokens": triage.input_tokens,
            "ai_output_tokens": triage.output_tokens,
            "language": triage.language,
            "is_spam": triage.is_spam,
            "spam_score": triage.spam_score,
            "processing_status": Email.ProcessingStatus.COMPLETED,
        },
    )

    # Save attachment metadata (clear old ones on update, re-create)
    if email_msg.attachment_details:
        if not created:
            email_obj.attachments.all().delete()
        for att in email_msg.attachment_details:
            AttachmentMetadata.objects.create(
                email=email_obj,
                filename=att.get("filename", ""),
                size_bytes=att.get("size", 0),
                mime_type=att.get("mime_type", ""),
                gmail_attachment_id=att.get("attachment_id", ""),
            )

    # Set SLA deadlines (non-critical -- failure should not crash pipeline)
    try:
        set_sla_deadlines(email_obj)
    except Exception:
        logger.exception("Failed to set SLA deadlines for email %s", email_obj.pk)

    # Thread create/update (THRD-04)
    try:
        thread_id = email_msg.thread_id or email_msg.message_id
        thread, thread_created = Thread.objects.get_or_create(
            gmail_thread_id=thread_id,
            defaults={"subject": email_msg.subject},
        )
        email_obj.thread = thread
        email_obj.save(update_fields=["thread"])

        # Activity log
        if thread_created:
            ActivityLog.objects.create(
                thread=thread,
                email=email_obj,
                action=ActivityLog.Action.THREAD_CREATED,
                detail=f"Thread created from {email_msg.inbox}",
            )
        else:
            ActivityLog.objects.create(
                thread=thread,
                email=email_obj,
                action=ActivityLog.Action.NEW_EMAIL_RECEIVED,
                detail=f"New message from {email_msg.sender_email}",
            )

        # Reopen logic: any non-NEW thread reopens on new message
        is_reopen = False
        if not thread_created and thread.status != Thread.Status.NEW:
            old_status = thread.status
            thread.status = Thread.Status.NEW
            thread.save(update_fields=["status"])
            is_reopen = True
            ActivityLog.objects.create(
                thread=thread,
                email=email_obj,
                action=ActivityLog.Action.REOPENED,
                detail=f"Reopened by new message from {email_msg.sender_email}",
                old_value=old_status,
                new_value=Thread.Status.NEW,
            )

        # Update denormalized preview fields
        update_thread_preview(thread)

        # Attach metadata for notification routing
        email_obj._thread_created = thread_created
        email_obj._thread_reopened = is_reopen

    except Exception:
        logger.exception("Failed to handle thread for email %s", email_obj.pk)
        email_obj._thread_created = True  # Default: treat as new thread
        email_obj._thread_reopened = False

    action = "Created" if created else "Updated"
    logger.info(f"{action} email {email_msg.message_id}: {triage.category}/{triage.priority}")
    return email_obj


def _is_whitelisted(sender_email: str) -> bool:
    """Check if sender email or domain is in the spam whitelist.

    Case-insensitive matching on both email and domain entries.
    """
    from apps.emails.models import SpamWhitelist

    domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    return SpamWhitelist.objects.filter(
        db_models.Q(entry_type="email", entry__iexact=sender_email)
        | db_models.Q(entry_type="domain", entry__iexact=domain)
    ).exists()


CROSS_INBOX_DEDUP_WINDOW_MINUTES = 5


def _detect_cross_inbox_duplicate(email_msg: EmailMessage) -> Optional[Email]:
    """Check if this email is a cross-inbox duplicate.

    Dedup key: same gmail_thread_id + same sender_email within recent window.
    Returns the original Email if duplicate detected, None otherwise.
    """
    if not email_msg.thread_id:
        return None

    cutoff = email_msg.timestamp - timedelta(minutes=CROSS_INBOX_DEDUP_WINDOW_MINUTES)
    original = Email.objects.filter(
        gmail_thread_id=email_msg.thread_id,
        from_address=email_msg.sender_email,
        received_at__gte=cutoff,
    ).exclude(
        to_inbox=email_msg.inbox,  # Different inbox
    ).order_by("received_at").first()

    return original


def process_single_email(
    email_msg: EmailMessage,
    ai_processor,
    gmail_poller,
    spam_filter_fn,
    ai_enabled: bool = True,
    chat_enabled: bool = False,
) -> Optional[Email]:
    """Process a single email through the pipeline.

    Order: whitelist check -> spam filter -> AI triage -> save to DB -> label Gmail
    """
    try:
        # Step 0: Cross-inbox dedup check
        original = _detect_cross_inbox_duplicate(email_msg)
        if original:
            logger.info(
                f"Cross-inbox duplicate detected: {email_msg.message_id} "
                f"(original on {original.to_inbox}, duplicate on {email_msg.inbox})"
            )
            # Reuse original's triage result
            triage = TriageResult(
                category=original.category,
                priority=original.priority,
                summary=original.ai_summary,
                reasoning=original.ai_reasoning,
                language=original.language,
                tags=original.ai_tags or [],
                model_used=original.ai_model_used,
                input_tokens=0,
                output_tokens=0,
                is_spam=original.is_spam,
                spam_score=original.spam_score,
            )
            email_obj = save_email_to_db(email_msg, triage)
            email_obj._is_cross_inbox_duplicate = True
            email_obj._duplicate_inbox = email_msg.inbox
            gmail_poller.mark_processed(email_msg)
            return email_obj

        # Step 1: Spam filter (skip if sender is whitelisted)
        if _is_whitelisted(email_msg.sender_email):
            logger.info(f"Sender whitelisted, skipping spam filter: {email_msg.sender_email}")
            spam_result = None
        else:
            spam_result = spam_filter_fn(email_msg)
        if spam_result:
            logger.info(f"Spam detected: {email_msg.subject[:50]}")
            email_obj = save_email_to_db(email_msg, spam_result)
            email_obj._is_cross_inbox_duplicate = False
            gmail_poller.mark_processed(email_msg)
            return email_obj

        # Step 2: AI triage (or fallback if disabled)
        if ai_enabled:
            triage = ai_processor.process(email_msg, gmail_poller=gmail_poller)
        else:
            triage = AIProcessor._fallback_result("AI disabled")

        # Step 3: Save to DB (BEFORE labeling Gmail)
        email_obj = save_email_to_db(email_msg, triage)

        email_obj._is_cross_inbox_duplicate = False

        # Step 4: Label Gmail (AFTER successful DB persist -- label-after-persist)
        gmail_poller.mark_processed(email_msg)

        return email_obj

    except Exception as e:
        logger.error(f"Failed to process email {email_msg.message_id}: {e}")
        # Save as failed for retry
        try:
            email_obj, _ = Email.objects.update_or_create(
                message_id=email_msg.message_id,
                defaults={
                    "gmail_id": email_msg.message_id,
                    "gmail_thread_id": email_msg.thread_id,
                    "from_address": email_msg.sender_email,
                    "from_name": email_msg.sender_name,
                    "to_inbox": email_msg.inbox,
                    "subject": email_msg.subject,
                    "body": email_msg.body,
                    "body_html": getattr(email_msg, 'body_html', ''),
                    "received_at": email_msg.timestamp,
                    "gmail_link": email_msg.gmail_link,
                    "processing_status": Email.ProcessingStatus.FAILED,
                    "last_error": str(e)[:1000],
                },
            )
        except Exception as save_err:
            logger.error(f"Failed to save error state for {email_msg.message_id}: {save_err}")
        return None


def process_poll_cycle(gmail_poller, ai_processor, chat_notifier, state_manager):
    """Run a full poll-filter-triage-save cycle.

    Reads feature flags from SystemConfig. Respects circuit breaker.
    Calls close_old_connections() at start for Django DB connection management.
    """
    close_old_connections()

    # Read config
    mode = SystemConfig.get("operating_mode", "unknown")
    logger.info(f"Poll cycle starting (mode={mode})")

    ai_enabled = SystemConfig.get("ai_triage_enabled", True)
    chat_enabled = SystemConfig.get("chat_notifications_enabled", False)
    inboxes_str = SystemConfig.get("monitored_inboxes", "")
    max_failures = SystemConfig.get("max_consecutive_failures", 3)

    # Circuit breaker check
    if state_manager.consecutive_failures >= max_failures:
        logger.critical(
            f"Circuit breaker OPEN: {state_manager.consecutive_failures} consecutive failures "
            f"(threshold: {max_failures}). Skipping poll cycle."
        )
        return

    try:
        # Parse inboxes
        inboxes = [i.strip() for i in inboxes_str.split(",") if i.strip()]

        # Poll for new emails
        new_emails = gmail_poller.poll_all(inboxes)
        if not new_emails:
            logger.debug("No new emails found")
            state_manager.reset_failures()
            return

        processed_items = []
        for email_msg in new_emails:
            # Dedup: skip if already in DB
            if Email.objects.filter(message_id=email_msg.message_id).exists():
                logger.debug(f"Dedup: skipping {email_msg.message_id} (already in DB)")
                continue

            email_obj = process_single_email(
                email_msg=email_msg,
                ai_processor=ai_processor,
                gmail_poller=gmail_poller,
                spam_filter_fn=spam_filter_fn_default,
                ai_enabled=ai_enabled,
                chat_enabled=chat_enabled,
            )
            if email_obj:
                processed_items.append(email_obj)

        # Send Chat notifications -- route new threads vs thread updates vs cross-inbox dups
        if chat_enabled and processed_items and chat_notifier:
            cross_inbox_dups = [e for e in processed_items if getattr(e, "_is_cross_inbox_duplicate", False)]
            non_dup_items = [e for e in processed_items if not getattr(e, "_is_cross_inbox_duplicate", False)]
            new_thread_emails = [e for e in non_dup_items if getattr(e, "_thread_created", True)]
            thread_update_emails = [e for e in non_dup_items if not getattr(e, "_thread_created", True)]

            if new_thread_emails:
                try:
                    chat_notifier.notify_new_emails(new_thread_emails)
                except Exception as e:
                    logger.error(f"Chat notification (new threads) failed: {e}")

            for e in thread_update_emails:
                try:
                    reopened = getattr(e, "_thread_reopened", False)
                    chat_notifier.notify_thread_update(e, reopened=reopened)
                except Exception as e_err:
                    logger.error(f"Chat notification (thread update) failed: {e_err}")

            for dup_email in cross_inbox_dups:
                try:
                    chat_notifier.notify_cross_inbox_duplicate(dup_email)
                except Exception as e_err:
                    logger.error(f"Cross-inbox dup notification failed: {e_err}")

        state_manager.reset_failures()
        logger.info(f"Poll cycle complete: {len(processed_items)} email(s) processed")

    except Exception as e:
        state_manager.record_failure()
        logger.error(f"Poll cycle failed: {e}")


def retry_failed_emails(ai_processor, gmail_poller):
    """Retry emails with processing_status='failed' and retry_count < 3.

    After 3rd retry failure, marks email as 'exhausted' (terminal state).
    """
    close_old_connections()

    failed_emails = (
        Email.objects.filter(
            processing_status=Email.ProcessingStatus.FAILED,
            retry_count__lt=3,
        )
        .order_by("created_at")[:10]
    )

    for email_obj in failed_emails:
        email_obj.retry_count += 1
        try:
            # Reconstruct EmailMessage DTO from stored data
            email_msg = EmailMessage(
                thread_id=email_obj.gmail_thread_id,
                message_id=email_obj.message_id,
                inbox=email_obj.to_inbox,
                sender_name=email_obj.from_name,
                sender_email=email_obj.from_address,
                subject=email_obj.subject,
                body=email_obj.body,
                timestamp=email_obj.received_at,
                gmail_link=email_obj.gmail_link,
                body_html=getattr(email_obj, 'body_html', ''),
            )

            triage = ai_processor.process(email_msg, gmail_poller=gmail_poller)

            # Update with successful triage
            email_obj.category = triage.category
            email_obj.priority = triage.priority
            email_obj.ai_summary = triage.summary
            email_obj.ai_reasoning = triage.reasoning
            email_obj.ai_model_used = triage.model_used
            email_obj.ai_tags = triage.tags
            email_obj.ai_suggested_assignee = _map_suggested_assignee(triage)
            email_obj.ai_input_tokens = triage.input_tokens
            email_obj.ai_output_tokens = triage.output_tokens
            email_obj.language = triage.language
            email_obj.processing_status = Email.ProcessingStatus.COMPLETED
            email_obj.last_error = ""
            email_obj.save()

            logger.info(f"Retry successful for {email_obj.message_id} (attempt {email_obj.retry_count})")

        except Exception as e:
            logger.error(f"Retry failed for {email_obj.message_id} (attempt {email_obj.retry_count}): {e}")
            email_obj.last_error = str(e)[:1000]

            if email_obj.retry_count >= 3:
                email_obj.processing_status = Email.ProcessingStatus.EXHAUSTED
                logger.warning(f"Email {email_obj.message_id} exhausted after 3 retries")

            email_obj.save()
