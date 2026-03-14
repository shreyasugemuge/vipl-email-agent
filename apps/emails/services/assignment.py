"""Assignment service -- assign emails, change status, send notifications.

Core action layer: manager assigns emails, team members acknowledge/close,
everyone gets notified via Chat and email.
"""

import logging
import os

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from django.db import close_old_connections

from apps.core.models import SystemConfig
from apps.emails.models import ActivityLog, AssignmentRule, CategoryVisibility, Email
from apps.emails.services.chat_notifier import ChatNotifier

logger = logging.getLogger(__name__)


def _send_assignment_chat(email, assignee):
    """Send assignment Chat notification to the right webhook(s).

    Routing: category webhook (if configured) → global webhook (fallback).
    Both fire if both are set and different.
    """
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
