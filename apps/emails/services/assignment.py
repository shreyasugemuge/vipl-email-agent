"""Assignment service -- assign emails/threads, change status, send notifications.

Core action layer: manager assigns emails/threads, team members acknowledge/close,
everyone gets notified via Chat and email.
"""

import logging
import os
import re

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from django.db import close_old_connections

from apps.core.models import SystemConfig
from apps.emails.models import ActivityLog, AssignmentRule, CategoryVisibility, Email, Thread
from apps.emails.services.chat_notifier import ChatNotifier

logger = logging.getLogger(__name__)


# ===========================================================================
# @mention utilities
# ===========================================================================


def parse_mentions(body):
    """Extract @mentioned usernames from note body text.

    Pattern: @username where username contains word chars and dots.
    Returns a deduplicated list of username strings (not User objects).
    """
    if not body:
        return []
    matches = re.findall(r"@([\w.]+)", body)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def notify_mention(thread, note_author, mentioned_user):
    """Send @mention notification via Google Chat and email. Fire-and-forget.

    Never raises -- logs errors and returns silently.
    """
    author_name = note_author.get_full_name() or note_author.username
    subject_line = thread.subject or "(no subject)"

    # Chat notification (lightweight text, not full Cards v2)
    try:
        if not SystemConfig.get("chat_notifications_enabled", False):
            webhook_url = ""
        else:
            webhook_url = (
                SystemConfig.get("chat_webhook_url", "")
                or os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")
            )
        if webhook_url:
            notifier = ChatNotifier(webhook_url=webhook_url)
            text = f"{author_name} mentioned you in a note on: {subject_line}"
            notifier._post({"text": text})
    except Exception:
        logger.exception(
            "Chat mention notification failed for thread %s, user %s",
            thread.pk, mentioned_user.username,
        )

    # Email notification
    try:
        if mentioned_user.email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "triage@vidarbhainfotech.com")
            send_mail(
                subject=f"{author_name} mentioned you: {subject_line[:60]}",
                message=(
                    f"{author_name} mentioned you in a note on thread: {subject_line}\n\n"
                    f"View in dashboard: /emails/\n"
                ),
                from_email=from_email,
                recipient_list=[mentioned_user.email],
                fail_silently=False,
            )
    except Exception:
        logger.exception(
            "Email mention notification failed for thread %s, user %s",
            thread.pk, mentioned_user.username,
        )


def _send_assignment_chat(email, assignee):
    """Send assignment Chat notification to the right webhook(s).

    Routing: category webhook (if configured) → global webhook (fallback).
    Both fire if both are set and different.
    Skipped entirely when chat_notifications_enabled is false.
    """
    if not SystemConfig.get("chat_notifications_enabled", False):
        return

    global_webhook = SystemConfig.get("chat_webhook_url", "") or os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")
    category = getattr(email, "category", "") or ""
    category_webhook = ""
    if category:
        category_webhook = SystemConfig.get(f"chat_webhook_{category.lower()}", "") or ""

    sent_urls = set()

    # Send to category-specific webhook first
    if category_webhook:
        notifier = ChatNotifier(webhook_url=category_webhook)
        notifier.notify_assignment(email, assignee)
        sent_urls.add(category_webhook)

    # Also send to global webhook (for manager visibility) unless same URL
    if global_webhook and global_webhook not in sent_urls:
        notifier = ChatNotifier(webhook_url=global_webhook)
        notifier.notify_assignment(email, assignee)


def _user_display(user):
    """Return best display name for a user."""
    if user is None:
        return ""
    full = user.get_full_name()
    return full if full.strip() else user.username


def assign_email(email, assignee, assigned_by, note=""):
    """Assign (or reassign) an email to a team member.

    Sets assigned_to, assigned_by, assigned_at on the Email.
    Creates an ActivityLog entry. Fires Chat + email notifications
    (fire-and-forget -- failures logged, never crash).

    Returns the updated Email instance.
    """
    old_assignee = email.assigned_to

    # Update email fields
    email.assigned_to = assignee
    email.assigned_by = assigned_by
    email.assigned_at = timezone.now()
    email.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "updated_at"])

    # Determine action type
    if old_assignee:
        action = ActivityLog.Action.REASSIGNED
        old_value = _user_display(old_assignee)
    else:
        action = ActivityLog.Action.ASSIGNED
        old_value = ""

    new_value = _user_display(assignee)

    # Create activity log
    ActivityLog.objects.create(
        email=email,
        user=assigned_by,
        action=action,
        detail=note,
        old_value=old_value,
        new_value=new_value,
    )

    # Fire-and-forget: Chat notification
    try:
        _send_assignment_chat(email, assignee)
    except Exception:
        logger.exception("Chat notification failed for assignment of email %s", email.pk)

    # Fire-and-forget: Email notification (only if enabled)
    try:
        if SystemConfig.get("email_notifications_enabled", False):
            notify_assignment_email(email, assignee)
    except Exception:
        logger.exception("Email notification failed for assignment of email %s", email.pk)

    return email


def change_status(email, new_status, changed_by):
    """Change the status of an email and log the activity.

    Validates new_status against Email.Status.values.
    Returns the updated Email instance.
    """
    valid_statuses = [s.value for s in Email.Status]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

    old_status = email.status
    email.status = new_status
    email.save(update_fields=["status", "updated_at"])

    # Map status to activity log action
    action_map = {
        "acknowledged": ActivityLog.Action.ACKNOWLEDGED,
        "closed": ActivityLog.Action.CLOSED,
    }
    action = action_map.get(new_status, ActivityLog.Action.STATUS_CHANGED)

    ActivityLog.objects.create(
        email=email,
        user=changed_by,
        action=action,
        old_value=old_status,
        new_value=new_status,
    )

    return email


def notify_assignment_email(email, assignee):
    """Send email notification to assignee about the assignment.

    Returns True on success, False on failure. Never raises.
    """
    if not assignee.email:
        logger.warning("Cannot send assignment email -- assignee %s has no email", assignee.username)
        return False

    subject = f"Email assigned to you: {email.subject[:60]}"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "triage@vidarbhainfotech.com")

    summary = (email.ai_summary or "")[:200]
    dashboard_url = f"/emails/?selected={email.pk}"

    body = (
        f"An email has been assigned to you.\n\n"
        f"From: {email.from_name} <{email.from_address}>\n"
        f"Priority: {email.priority}\n"
        f"Category: {email.category}\n"
        f"Summary: {summary}\n\n"
        f"View in dashboard: {dashboard_url}\n"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[assignee.email],
            fail_silently=False,
        )
        logger.info("Assignment email sent to %s for email %s", assignee.email, email.pk)
        return True
    except Exception:
        logger.exception("Failed to send assignment email to %s", assignee.email)
        return False


def auto_assign_batch():
    """Auto-assign unassigned emails to team members based on assignment rules.

    Finds unassigned, NEW, COMPLETED, non-spam emails and matches them
    to AssignmentRule entries by category. Assigns to the first-priority
    active person. Uses optimistic locking to prevent race conditions.

    Returns the number of emails assigned.
    """
    close_old_connections()

    unassigned = Email.objects.filter(
        assigned_to__isnull=True,
        status=Email.Status.NEW,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    )

    assigned_count = 0

    for email in unassigned:
        # Find matching rules for this category
        rule = (
            AssignmentRule.objects.filter(
                category=email.category,
                is_active=True,
                assignee__is_active=True,
            )
            .order_by("priority_order")
            .first()
        )

        if not rule:
            continue

        # Optimistic locking: re-check unassigned before update
        updated = Email.objects.filter(
            pk=email.pk,
            assigned_to__isnull=True,
        ).update(
            assigned_to=rule.assignee,
            assigned_by=None,
            assigned_at=timezone.now(),
        )

        if updated:
            # Create activity log
            ActivityLog.objects.create(
                email=email,
                user=None,  # system action
                action=ActivityLog.Action.AUTO_ASSIGNED,
                detail=f"Auto-assigned by category rule: {email.category}",
                new_value=_user_display(rule.assignee),
            )

            # Fire-and-forget notifications
            try:
                _send_assignment_chat(email, rule.assignee)
            except Exception:
                logger.exception("Chat notification failed for auto-assign of email %s", email.pk)

            try:
                if SystemConfig.get("email_notifications_enabled", False):
                    notify_assignment_email(email, rule.assignee)
            except Exception:
                logger.exception("Email notification failed for auto-assign of email %s", email.pk)

            assigned_count += 1
            logger.info(
                "Auto-assigned email %s (%s) to %s",
                email.pk, email.category, _user_display(rule.assignee),
            )

    logger.info("Auto-assign batch complete: %d emails assigned", assigned_count)
    return assigned_count


def claim_email(email, claimed_by):
    """Allow a team member to self-claim an unassigned email.

    Validates:
    1. Email is not already assigned (raises ValueError)
    2. User has CategoryVisibility for the email's category,
       unless user is admin/staff (raises PermissionError)

    Uses assign_email() internally, then updates the ActivityLog
    action to CLAIMED.

    Returns the updated Email instance.
    """
    if email.assigned_to is not None:
        raise ValueError(
            f"Email {email.pk} is already assigned to {_user_display(email.assigned_to)}"
        )

    # Admin/staff bypasses visibility check
    if not (claimed_by.is_staff or claimed_by.role == "admin"):
        has_visibility = CategoryVisibility.objects.filter(
            user=claimed_by,
            category=email.category,
        ).exists()
        if not has_visibility:
            raise PermissionError(
                f"User {claimed_by.username} lacks category visibility for '{email.category}'"
            )

    # Use existing assign_email for the heavy lifting
    result = assign_email(email, claimed_by, assigned_by=claimed_by, note="Self-claimed")

    # Update the last activity log entry from ASSIGNED to CLAIMED
    last_log = ActivityLog.objects.filter(
        email=email,
        action=ActivityLog.Action.ASSIGNED,
    ).order_by("-created_at").first()

    if last_log:
        last_log.action = ActivityLog.Action.CLAIMED
        last_log.save(update_fields=["action"])

    return result


# ===========================================================================
# Thread-level assignment functions
# ===========================================================================


def assign_thread(thread, assignee, assigned_by, note=""):
    """Assign (or reassign) a thread to a team member.

    Sets assigned_to, assigned_by, assigned_at on the Thread.
    Creates an ActivityLog entry with thread FK (email=None).
    Fires Chat + email notifications (fire-and-forget).

    Returns the updated Thread instance.
    """
    old_assignee = thread.assigned_to

    # Update thread fields
    thread.assigned_to = assignee
    thread.assigned_by = assigned_by
    thread.assigned_at = timezone.now()
    thread.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "updated_at"])

    # Determine action type
    if old_assignee:
        action = ActivityLog.Action.REASSIGNED
        old_value = _user_display(old_assignee)
    else:
        action = ActivityLog.Action.ASSIGNED
        old_value = ""

    new_value = _user_display(assignee)

    # Create activity log (thread-level, no email)
    ActivityLog.objects.create(
        thread=thread,
        email=None,
        user=assigned_by,
        action=action,
        detail=note,
        old_value=old_value,
        new_value=new_value,
    )

    # Fire-and-forget: Chat notification
    # Thread has .subject, .category, .priority, .pk — same attributes ChatNotifier uses
    try:
        _send_assignment_chat(thread, assignee)
    except Exception:
        logger.exception("Chat notification failed for assignment of thread %s", thread.pk)

    # Fire-and-forget: Email notification (only if enabled)
    try:
        if SystemConfig.get("email_notifications_enabled", False):
            notify_assignment_email(thread, assignee)
    except Exception:
        logger.exception("Email notification failed for assignment of thread %s", thread.pk)

    return thread


def change_thread_status(thread, new_status, changed_by):
    """Change the status of a thread and log the activity.

    Validates new_status against Thread.Status.values.
    Returns the updated Thread instance.
    """
    valid_statuses = [s.value for s in Thread.Status]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

    old_status = thread.status
    thread.status = new_status
    thread.save(update_fields=["status", "updated_at"])

    # Map status to activity log action
    action_map = {
        "acknowledged": ActivityLog.Action.ACKNOWLEDGED,
        "closed": ActivityLog.Action.CLOSED,
    }
    action = action_map.get(new_status, ActivityLog.Action.STATUS_CHANGED)

    ActivityLog.objects.create(
        thread=thread,
        email=None,
        user=changed_by,
        action=action,
        old_value=old_status,
        new_value=new_status,
    )

    return thread


def claim_thread(thread, claimed_by):
    """Allow a team member to self-claim an unassigned thread.

    Validates:
    1. Thread is not already assigned (raises ValueError)
    2. User has CategoryVisibility for the thread's category,
       unless user is admin/staff (raises PermissionError)

    Uses assign_thread() internally, then updates the ActivityLog
    action to CLAIMED.

    Returns the updated Thread instance.
    """
    if thread.assigned_to is not None:
        raise ValueError(
            f"Thread {thread.pk} is already assigned to {_user_display(thread.assigned_to)}"
        )

    # Admin/gatekeeper/staff bypasses visibility check
    if not claimed_by.can_assign:
        has_visibility = CategoryVisibility.objects.filter(
            user=claimed_by,
            category=thread.category,
        ).exists()
        if not has_visibility:
            raise PermissionError(
                f"User {claimed_by.username} lacks category visibility for '{thread.category}'"
            )

    # Use assign_thread for the heavy lifting
    result = assign_thread(thread, claimed_by, assigned_by=claimed_by, note="Self-claimed")

    # Update the last activity log entry from ASSIGNED to CLAIMED
    last_log = ActivityLog.objects.filter(
        thread=thread,
        action=ActivityLog.Action.ASSIGNED,
    ).order_by("-created_at").first()

    if last_log:
        last_log.action = ActivityLog.Action.CLAIMED
        last_log.save(update_fields=["action"])

    return result


def reassign_thread(thread, new_assignee, reassigned_by, reason):
    """Member-initiated reassignment with mandatory reason.

    Validates:
    1. reassigned_by is the current assigned_to (owns the thread)
    2. reason is non-empty after stripping whitespace
    3. new_assignee has CategoryVisibility for thread's category

    Creates REASSIGNED_BY_MEMBER ActivityLog with reason in detail field.
    """
    if not reason or not reason.strip():
        raise ValueError("A reason is required when reassigning.")

    if thread.assigned_to != reassigned_by:
        raise PermissionError("You can only reassign threads assigned to you.")

    # Check new_assignee has CategoryVisibility for this thread's category
    has_visibility = CategoryVisibility.objects.filter(
        user=new_assignee, category=thread.category,
    ).exists()
    if not has_visibility:
        raise PermissionError(
            f"{new_assignee.get_full_name()} does not handle {thread.category} threads."
        )

    old_assignee_name = _user_display(thread.assigned_to)

    thread.assigned_to = new_assignee
    thread.assigned_by = reassigned_by
    thread.assigned_at = timezone.now()
    thread.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "updated_at"])

    ActivityLog.objects.create(
        thread=thread,
        user=reassigned_by,
        action=ActivityLog.Action.REASSIGNED_BY_MEMBER,
        detail=reason.strip(),
        old_value=old_assignee_name,
        new_value=_user_display(new_assignee),
    )

    return thread


def update_thread_preview(thread):
    """Update denormalized preview fields on a thread from its emails.

    Sets: last_message_at, last_sender, last_sender_address (from latest email)
    Sets: subject (from earliest email)
    Sets: category, priority, ai_summary, ai_draft_reply (from latest COMPLETED email)

    Returns None if thread has no emails (no-op).
    """
    latest_email = thread.emails.order_by("-received_at").first()
    if latest_email is None:
        return None

    # Latest email -> preview fields
    thread.last_message_at = latest_email.received_at
    thread.last_sender = latest_email.from_name
    thread.last_sender_address = latest_email.from_address

    # Earliest email -> subject
    earliest_email = thread.emails.order_by("received_at").first()
    if earliest_email:
        thread.subject = earliest_email.subject

    # Latest COMPLETED email -> triage fields
    latest_triaged = (
        thread.emails
        .filter(processing_status=Email.ProcessingStatus.COMPLETED)
        .order_by("-received_at")
        .first()
    )
    if latest_triaged:
        if not thread.category_overridden:
            thread.category = latest_triaged.category
        if not thread.priority_overridden:
            thread.priority = latest_triaged.priority
        thread.ai_summary = latest_triaged.ai_summary
        thread.ai_draft_reply = latest_triaged.ai_draft_reply
        thread.ai_confidence = latest_triaged.ai_confidence

    thread.save(update_fields=[
        "last_message_at", "last_sender", "last_sender_address",
        "subject", "category", "priority", "ai_summary", "ai_draft_reply",
        "ai_confidence", "updated_at",
    ])

    return thread
