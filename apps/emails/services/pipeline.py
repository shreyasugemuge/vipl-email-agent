"""Pipeline orchestrator -- wires poll, filter, triage, save, and label.

This is the ONLY service module that imports Django ORM. Per locked
decision: "GmailPoller returns EmailMessage, a save step maps it to
the Email model."

Flow: poll -> dedup -> spam filter -> AI triage -> save to DB -> label Gmail
Safety: label-after-persist (Gmail label only applied after DB write succeeds)
"""

import logging
import time
from datetime import timedelta
from typing import Optional

from django.db import close_old_connections, transaction

from django.db import models as db_models

from apps.core.models import SystemConfig
from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    AssignmentRule,
    AttachmentMetadata,
    Email,
    PollLog,
    SenderReputation,
    Thread,
    ThreadReadState,
)
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
            parts = name.strip().split()
            first = parts[0]
            last = parts[-1] if len(parts) > 1 else None
            user = None
            # Exact first+last match
            if last:
                user = User.objects.filter(
                    first_name__iexact=first, last_name__iexact=last, is_active=True,
                ).first()
            # First name only
            if not user:
                user = User.objects.filter(first_name__iexact=first, is_active=True).first()
            # Username fallback
            if not user:
                user = User.objects.filter(username__iexact=first, is_active=True).first()
            if user:
                detail["user_id"] = user.pk
        except Exception:
            pass  # Non-critical -- user_id is a convenience field

    return detail


def _try_inline_auto_assign(thread, triage):
    """Attempt inline auto-assign for HIGH confidence threads.

    Uses optimistic locking to prevent race conditions with batch auto-assign.
    Non-critical -- failures are logged and swallowed.
    """
    try:
        # Check spam
        if triage.is_spam:
            return

        # Check confidence tier (default "100" = disabled, set to "HIGH" to enable)
        threshold = SystemConfig.get("auto_assign_confidence_tier", "100")
        if triage.confidence != threshold:
            return

        # Find matching rule
        rule = (
            AssignmentRule.objects.filter(
                category=triage.category,
                is_active=True,
                assignee__is_active=True,
            )
            .order_by("priority_order")
            .first()
        )
        if not rule:
            return

        # Optimistic locking: only assign if still unassigned
        from django.utils import timezone as tz

        updated = Thread.objects.filter(
            pk=thread.pk,
            assigned_to__isnull=True,
        ).update(
            assigned_to=rule.assignee,
            assigned_by=None,
            assigned_at=tz.now(),
            is_auto_assigned=True,
        )

        if updated:
            # Record auto-assign feedback
            AssignmentFeedback.objects.create(
                thread=thread,
                suggested_user=rule.assignee,
                actual_user=rule.assignee,
                action=AssignmentFeedback.FeedbackAction.AUTO_ASSIGNED,
                confidence_at_time=triage.confidence,
                user_who_acted=None,
            )

            assignee_name = rule.assignee.get_full_name() or rule.assignee.username
            ActivityLog.objects.create(
                thread=thread,
                action=ActivityLog.Action.AUTO_ASSIGNED,
                detail=f"Auto-assigned (HIGH confidence, rule: {triage.category})",
                new_value=assignee_name,
            )

            logger.info("Inline auto-assigned thread %s to %s", thread.pk, rule.assignee)

    except Exception:
        logger.exception("Inline auto-assign failed for thread %s", thread.pk)


def _create_unread_states_for_all_users(thread):
    """Bulk-create ThreadReadState(is_read=False) for all active users.

    Uses update_or_create pattern via bulk_create(ignore_conflicts=True)
    so reopened threads reset existing read states to unread.
    """
    from apps.accounts.models import User

    active_users = User.objects.filter(is_active=True)
    if not active_users.exists():
        return

    # For reopened threads, reset existing read states to unread
    ThreadReadState.objects.filter(thread=thread).update(is_read=False, read_at=None)

    # Create any missing read states (new users since thread was created)
    existing_user_ids = set(
        ThreadReadState.objects.filter(thread=thread).values_list("user_id", flat=True)
    )
    new_states = [
        ThreadReadState(thread=thread, user=u, is_read=False)
        for u in active_users
        if u.pk not in existing_user_ids
    ]
    if new_states:
        ThreadReadState.objects.bulk_create(new_states, ignore_conflicts=True)


def save_email_to_db(email_msg: EmailMessage, triage: TriageResult) -> Email:
    """Create or update an Email record from EmailMessage + TriageResult.

    Uses update_or_create with message_id as lookup key for dedup.
    Also saves AttachmentMetadata for each attachment.
    """
    with transaction.atomic():
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
                "headers": email_msg.headers,
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
                "ai_confidence": triage.confidence,
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

            # Create ThreadReadState(is_read=False) for all active users on new threads
            if thread_created:
                _create_unread_states_for_all_users(thread)

            # Reopen logic: any non-NEW/non-REOPENED thread reopens on new message
            is_reopen = False
            if not thread_created and thread.status not in (
                Thread.Status.NEW,
                Thread.Status.REOPENED,
            ):
                old_status = thread.status
                thread.status = Thread.Status.REOPENED
                thread.save(update_fields=["status"])
                is_reopen = True
                ActivityLog.objects.create(
                    thread=thread,
                    email=email_obj,
                    action=ActivityLog.Action.REOPENED,
                    detail=f"Reopened by new message from {email_msg.sender_email}",
                    old_value=old_status,
                    new_value=Thread.Status.REOPENED,
                )
                # Mark all users as unread on reopen
                _create_unread_states_for_all_users(thread)

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


def _is_blocked(sender_email: str) -> bool:
    """Check if sender is blocked via SenderReputation.

    Case-insensitive matching on sender address.
    """
    return SenderReputation.objects.filter(
        sender_address__iexact=sender_email,
        is_blocked=True,
    ).exists()


def _track_sender_reputation(sender_email: str, is_spam: bool) -> None:
    """Increment SenderReputation counters after saving an email.

    Uses F() expressions for atomic updates, then checks auto-block threshold.
    """
    from django.db.models import F

    sender = sender_email.strip().lower()
    if not sender:
        return

    rep, created = SenderReputation.objects.get_or_create(
        sender_address=sender,
        defaults={"total_count": 0, "spam_count": 0},
    )

    update_kwargs = {"total_count": F("total_count") + 1}
    if is_spam:
        update_kwargs["spam_count"] = F("spam_count") + 1

    SenderReputation.objects.filter(pk=rep.pk).update(**update_kwargs)
    rep.refresh_from_db()

    # Auto-block threshold: ratio > 0.8 AND total >= 3
    if rep.total_count >= 3 and rep.spam_ratio > 0.8 and not rep.is_blocked:
        rep.is_blocked = True
        rep.save(update_fields=["is_blocked"])


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

        # Step 1a: Block check (whitelisted senders bypass block)
        if not _is_whitelisted(email_msg.sender_email) and _is_blocked(email_msg.sender_email):
            logger.info(f"Sender blocked, skipping: {email_msg.sender_email}")
            return None

        # Step 1b: Spam filter (skip if sender is whitelisted)
        if _is_whitelisted(email_msg.sender_email):
            logger.info(f"Sender whitelisted, skipping spam filter: {email_msg.sender_email}")
            spam_result = None
        else:
            spam_result = spam_filter_fn(email_msg)
        if spam_result:
            logger.info(f"Spam detected: {email_msg.subject[:50]}")
            email_obj = save_email_to_db(email_msg, spam_result)
            try:
                _track_sender_reputation(email_msg.sender_email, is_spam=True)
            except Exception:
                logger.exception("Failed to track sender reputation for %s", email_msg.sender_email)
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

        # Step 3b: Track sender reputation
        try:
            _track_sender_reputation(email_msg.sender_email, is_spam=triage.is_spam)
        except Exception:
            logger.exception("Failed to track sender reputation for %s", email_msg.sender_email)

        email_obj._is_cross_inbox_duplicate = False

        # Step 3.5: Inline auto-assign for HIGH confidence threads
        if (
            not triage.is_spam
            and triage.confidence
            and email_obj.thread
            and email_obj.thread.assigned_to is None
        ):
            _try_inline_auto_assign(email_obj.thread, triage)

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

    from django.utils import timezone as tz
    poll_started_at = tz.now()
    poll_start_time = time.time()

    # Circuit breaker check
    if state_manager.consecutive_failures >= max_failures:
        logger.critical(
            f"Circuit breaker OPEN: {state_manager.consecutive_failures} consecutive failures "
            f"(threshold: {max_failures}). Skipping poll cycle."
        )
        _create_poll_log(
            started_at=poll_started_at,
            status="skipped",
            duration_ms=int((time.time() - poll_start_time) * 1000),
            skipped_reason=f"Circuit breaker open ({state_manager.consecutive_failures} failures)",
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
            # Persist last_poll_epoch even on empty polls (keeps inspector countdown accurate)
            try:
                now_epoch = str(int(time.time()))
                SystemConfig.objects.update_or_create(
                    key="last_poll_epoch",
                    defaults={
                        "value": now_epoch,
                        "value_type": SystemConfig.ValueType.INT,
                        "description": "Epoch timestamp of last successful poll cycle (deploy safety)",
                        "category": "scheduler",
                    },
                )
            except Exception as cfg_err:
                logger.warning(f"Failed to persist last_poll_epoch: {cfg_err}")
            _create_poll_log(
                started_at=poll_started_at,
                status="success",
                duration_ms=int((time.time() - poll_start_time) * 1000),
            )
            return

        processed_items = []
        spam_count = 0
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
                if email_obj.is_spam:
                    spam_count += 1

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

        # Persist last_poll_epoch so restarts skip first-poll catch-up
        try:
            now_epoch = str(int(time.time()))
            SystemConfig.objects.update_or_create(
                key="last_poll_epoch",
                defaults={
                    "value": now_epoch,
                    "value_type": SystemConfig.ValueType.INT,
                    "description": "Epoch timestamp of last successful poll cycle (deploy safety)",
                    "category": "scheduler",
                },
            )
        except Exception as cfg_err:
            logger.warning(f"Failed to persist last_poll_epoch: {cfg_err}")

        duration_ms = int((time.time() - poll_start_time) * 1000)
        _create_poll_log(
            started_at=poll_started_at,
            status="success",
            emails_found=len(new_emails),
            emails_processed=len(processed_items),
            spam_filtered=spam_count,
            duration_ms=duration_ms,
        )

        logger.info(f"Poll cycle complete: {len(processed_items)} email(s) processed")

    except Exception as e:
        state_manager.record_failure()
        duration_ms = int((time.time() - poll_start_time) * 1000)
        _create_poll_log(
            started_at=poll_started_at,
            status="error",
            duration_ms=duration_ms,
            error_message=str(e)[:1000],
        )
        logger.error(f"Poll cycle failed: {e}")


def _create_poll_log(*, started_at, status, emails_found=0, emails_processed=0,
                     spam_filtered=0, duration_ms=0, error_message="", skipped_reason=""):
    """Create a PollLog entry. Non-critical — failures are logged and swallowed."""
    try:
        PollLog.objects.create(
            started_at=started_at,
            status=status,
            emails_found=emails_found,
            emails_processed=emails_processed,
            spam_filtered=spam_filtered,
            duration_ms=duration_ms,
            error_message=error_message,
            skipped_reason=skipped_reason,
        )
    except Exception as log_err:
        logger.warning(f"Failed to create PollLog: {log_err}")


RETRY_BATCH_SIZE = 10


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
        .order_by("created_at")[:RETRY_BATCH_SIZE]
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
