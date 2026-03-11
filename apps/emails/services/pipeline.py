"""Pipeline orchestrator -- wires poll, filter, triage, save, and label.

This is the ONLY service module that imports Django ORM. Per locked
decision: "GmailPoller returns EmailMessage, a save step maps it to
the Email model."

Flow: poll -> dedup -> spam filter -> AI triage -> save to DB -> label Gmail
Safety: label-after-persist (Gmail label only applied after DB write succeeds)
"""

import logging
from typing import Optional

from django.db import close_old_connections

from apps.core.models import SystemConfig
from apps.emails.models import AttachmentMetadata, Email
from apps.emails.services.ai_processor import AIProcessor
from apps.emails.services.dtos import EmailMessage, TriageResult
from apps.emails.services.spam_filter import is_spam as spam_filter_fn_default

logger = logging.getLogger(__name__)


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
            "received_at": email_msg.timestamp,
            "gmail_link": email_msg.gmail_link,
            # AI triage fields
            "category": triage.category,
            "priority": triage.priority,
            "ai_summary": triage.summary,
            "ai_draft_reply": triage.draft_reply,
            "ai_reasoning": triage.reasoning,
            "ai_model_used": triage.model_used,
            "ai_tags": triage.tags,
            "ai_suggested_assignee": triage.suggested_assignee,
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

    action = "Created" if created else "Updated"
    logger.info(f"{action} email {email_msg.message_id}: {triage.category}/{triage.priority}")
    return email_obj


def process_single_email(
    email_msg: EmailMessage,
    ai_processor,
    gmail_poller,
    spam_filter_fn,
    ai_enabled: bool = True,
    chat_enabled: bool = False,
) -> Optional[Email]:
    """Process a single email through the pipeline.

    Order: spam filter -> AI triage -> save to DB -> label Gmail (label-after-persist)
    """
    try:
        # Step 1: Spam filter
        spam_result = spam_filter_fn(email_msg)
        if spam_result:
            logger.info(f"Spam detected: {email_msg.subject[:50]}")
            email_obj = save_email_to_db(email_msg, spam_result)
            gmail_poller.mark_processed(email_msg)
            return email_obj

        # Step 2: AI triage (or fallback if disabled)
        if ai_enabled:
            triage = ai_processor.process(email_msg, gmail_poller=gmail_poller)
        else:
            triage = AIProcessor._fallback_result("AI disabled")

        # Step 3: Save to DB (BEFORE labeling Gmail)
        email_obj = save_email_to_db(email_msg, triage)

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

        # Chat notification (placeholder -- Chat notifier built in Plan 03)
        if chat_enabled and processed_items and chat_notifier:
            try:
                chat_notifier.notify_new_emails(processed_items)
            except Exception as e:
                logger.error(f"Chat notification failed: {e}")

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
            )

            triage = ai_processor.process(email_msg, gmail_poller=gmail_poller)

            # Update with successful triage
            email_obj.category = triage.category
            email_obj.priority = triage.priority
            email_obj.ai_summary = triage.summary
            email_obj.ai_draft_reply = triage.draft_reply
            email_obj.ai_reasoning = triage.reasoning
            email_obj.ai_model_used = triage.model_used
            email_obj.ai_tags = triage.tags
            email_obj.ai_suggested_assignee = triage.suggested_assignee
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
