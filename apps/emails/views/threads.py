"""Thread-level action endpoints: detail, assign, status, spam, bulk actions."""

import json
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.http import HttpResponse as _HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.emails.models import (
    ActivityLog, AssignmentFeedback, CategoryVisibility, Email,
    InternalNote, SenderReputation, SpamFeedback, SpamWhitelist,
    Thread, ThreadReadState, ThreadViewer,
)
from apps.emails.services.dtos import VALID_PRIORITIES
from apps.emails.services.assignment import assign_thread as _assign_thread
from apps.emails.services.assignment import change_thread_status as _change_thread_status
from apps.emails.services.assignment import claim_thread as _claim_thread
from apps.emails.services.assignment import reassign_thread as _reassign_thread
from apps.emails.services.assignment import notify_mention as _notify_mention
from apps.emails.services.assignment import parse_mentions

from .helpers import (
    _build_thread_detail_context,
    _check_member_thread_access,
    _get_team_members,
    _log_activity,
    _render_thread_detail_with_oob_card,
    _render_thread_list_response,
    _render_whitelist_tab,
    _require_admin,
    _resolve_user_by_name,
    _unspam_matching_emails,
    _update_sender_reputation,
    get_active_viewers,
)

logger = logging.getLogger(__name__)


@login_required
@require_POST
def accept_thread_suggestion(request, pk):
    """Accept AI suggested assignee for a thread -- assigns and records feedback."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to accept AI suggestions.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"), pk=pk,
    )

    # Get suggestion from latest completed email
    latest_email = (
        thread.emails
        .filter(processing_status=Email.ProcessingStatus.COMPLETED)
        .order_by("-received_at")
        .first()
    )
    suggestion = getattr(latest_email, "ai_suggested_assignee", None) or {}
    if not isinstance(suggestion, dict) or not suggestion.get("name"):
        return HttpResponseForbidden("No valid AI suggestion to accept.")

    # Resolve user_id — may already be present or need runtime lookup
    assignee = None
    if suggestion.get("user_id"):
        assignee = User.objects.filter(pk=suggestion["user_id"], is_active=True).first()
    if not assignee and suggestion.get("name"):
        assignee = _resolve_user_by_name(suggestion["name"])
    if not assignee:
        return HttpResponseForbidden(f"Could not resolve user \"{suggestion.get('name')}\".")

    # Assign thread
    thread.assigned_to = assignee
    thread.assigned_by = user
    thread.assigned_at = timezone.now()
    thread.is_auto_assigned = False
    thread.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "is_auto_assigned", "updated_at"])

    # Record feedback
    AssignmentFeedback.objects.create(
        thread=thread,
        email=latest_email,
        suggested_user=assignee,
        actual_user=assignee,
        action=AssignmentFeedback.FeedbackAction.ACCEPTED,
        confidence_at_time=thread.ai_confidence,
        user_who_acted=user,
    )

    # Activity log
    _log_activity(
        thread, user, ActivityLog.Action.ASSIGNED,
        detail=f"Accepted AI suggestion — assigned to {assignee.get_full_name() or assignee.username}",
    )

    # Re-render detail panel + OOB card swap
    return _render_thread_detail_with_oob_card(thread, request, user)


@login_required
@require_POST
def reject_thread_suggestion(request, pk):
    """Reject AI suggested assignee for a thread -- unassigns and records feedback."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to dismiss AI suggestions.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"), pk=pk,
    )

    # Get suggestion from latest completed email (for feedback recording)
    latest_email = (
        thread.emails
        .filter(processing_status=Email.ProcessingStatus.COMPLETED)
        .order_by("-received_at")
        .first()
    )
    suggestion = getattr(latest_email, "ai_suggested_assignee", None) or {}
    suggested_user = None
    if isinstance(suggestion, dict) and suggestion.get("user_id"):
        suggested_user = User.objects.filter(pk=suggestion["user_id"]).first()

    # Unassign thread
    thread.assigned_to = None
    thread.assigned_by = None
    thread.assigned_at = None
    thread.is_auto_assigned = False
    thread.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "is_auto_assigned", "updated_at"])

    # Record feedback
    AssignmentFeedback.objects.create(
        thread=thread,
        email=latest_email,
        suggested_user=suggested_user,
        actual_user=None,
        action=AssignmentFeedback.FeedbackAction.REJECTED,
        confidence_at_time=thread.ai_confidence,
        user_who_acted=user,
    )

    # Clear suggestion on latest email so suggestion bar disappears
    if latest_email:
        latest_email.ai_suggested_assignee = {}
        latest_email.save(update_fields=["ai_suggested_assignee", "updated_at"])

    # Re-render detail panel + OOB card swap
    return _render_thread_detail_with_oob_card(thread, request, user)


@login_required
@require_POST
def viewer_heartbeat(request, pk):
    """Update viewer presence and return the viewer badge partial."""
    from django.db import transaction

    with transaction.atomic():
        ThreadViewer.objects.update_or_create(
            thread_id=pk, user=request.user,
            defaults={"last_seen": timezone.now()},
        )
        # Opportunistic cleanup of stale records
        cutoff = timezone.now() - timedelta(seconds=30)
        ThreadViewer.objects.filter(thread_id=pk, last_seen__lt=cutoff).delete()

    active_viewers = get_active_viewers(pk, exclude_user_id=request.user.pk)
    html = render_to_string("emails/_viewer_badge.html", {"active_viewers": active_viewers}, request=request)
    return _HttpResponse(html)


@login_required
@require_POST
def clear_viewer(request, pk):
    """Remove the current user's viewer record for a thread."""
    ThreadViewer.objects.filter(thread_id=pk, user=request.user).delete()
    return _HttpResponse(status=204)


@login_required
@require_GET
def thread_detail(request, pk):
    """Return the thread detail panel partial for HTMX swap."""
    # Non-HTMX requests (e.g. links from activity page) → redirect to thread list
    if not getattr(request, "htmx", False):
        from django.urls import reverse
        return redirect(f"{reverse('emails:thread_list')}?open={pk}")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    user = request.user
    can_assign = user.can_assign

    # Members can only view threads assigned to them or unclaimed
    denied = _check_member_thread_access(thread, user)
    if denied:
        return denied

    team_members = []
    if can_assign:
        team_members = _get_team_members()

    # Register this user as viewing the thread
    ThreadViewer.objects.update_or_create(
        thread_id=pk, user=user,
        defaults={"last_seen": timezone.now()},
    )

    # Mark thread as read for this user
    ThreadReadState.objects.update_or_create(
        thread=thread, user=user,
        defaults={"is_read": True, "read_at": timezone.now()},
    )

    active_viewers = get_active_viewers(pk, exclude_user_id=user.pk)

    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    context["active_viewers"] = active_viewers

    # Return detail panel + OOB card swap to update read styling
    detail_response = render(request, "emails/_thread_detail.html", context)
    thread.is_unread = False
    card_html = render_to_string(
        "emails/_thread_card.html",
        {"thread": thread, "oob": True},
        request=request,
    )
    return _HttpResponse(detail_response.content.decode() + card_html)


@login_required
@require_POST
def mark_thread_unread(request, pk):
    """Mark a thread as unread for the current user."""
    thread = get_object_or_404(Thread, pk=pk)
    denied = _check_member_thread_access(thread, request.user)
    if denied:
        return denied
    ThreadReadState.objects.update_or_create(
        thread=thread, user=request.user,
        defaults={"is_read": False, "read_at": None},
    )
    # Return empty detail panel placeholder + OOB card swap
    thread.is_unread = True
    card_html = render_to_string(
        "emails/_thread_card.html",
        {"thread": thread, "oob": True},
        request=request,
    )
    close_html = (
        '<div id="thread-detail-panel" class="flex items-center justify-center h-full">'
        '<span class="font-pixel text-[8px] text-[var(--vipl-text-dim)]">Select a thread</span></div>'
    )
    return _HttpResponse(close_html + card_html)


@login_required
@require_POST
def edit_ai_summary(request, pk):
    """Edit the AI summary for a thread. Requires can_assign permission."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to edit AI summaries.")

    thread = get_object_or_404(Thread, pk=pk)
    new_summary = (request.POST.get("ai_summary") or "").strip()
    if new_summary:
        old_summary = thread.ai_summary
        thread.ai_summary = new_summary
        thread.save(update_fields=["ai_summary"])

        _log_activity(
            thread, user, ActivityLog.Action.AI_SUMMARY_EDITED,
            old_value=old_summary[:200],
            new_value=new_summary[:200],
            detail=f"AI summary edited by {user.get_full_name() or user.username}",
        )

    # Re-render the detail panel
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = _get_team_members()
    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    return render(request, "emails/_thread_detail.html", context)


@login_required
@require_POST
def edit_category(request, pk):
    """Inline edit: change thread category. Admin/gatekeeper or assigned user."""
    user = request.user
    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to"),
        pk=pk,
    )

    denied = _check_member_thread_access(thread, user)
    if denied:
        return denied

    category = (request.POST.get("category") or "").strip()
    if category == "__custom__":
        category = (request.POST.get("custom_category") or "").strip()
        if not category:
            return _HttpResponse("Custom category cannot be empty.", status=400)
        if len(category) > 100:
            return _HttpResponse("Custom category too long (max 100 chars).", status=400)

    old_category = thread.category
    thread.category = category
    thread.category_overridden = True
    thread.save(update_fields=["category", "category_overridden"])

    _log_activity(
        thread, user, ActivityLog.Action.CATEGORY_CHANGED,
        old_value=old_category[:200],
        new_value=category[:200],
        detail=f"Category changed by {user.get_full_name() or user.username}",
    )

    return _render_thread_detail_with_oob_card(thread, request, user)


@login_required
@require_POST
def edit_priority(request, pk):
    """Inline edit: change thread priority. Admin/gatekeeper or assigned user."""
    user = request.user
    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to"),
        pk=pk,
    )

    denied = _check_member_thread_access(thread, user)
    if denied:
        return denied

    new_priority = (request.POST.get("priority") or "").strip()
    if new_priority not in VALID_PRIORITIES:
        return _HttpResponse(f"Invalid priority: {new_priority}", status=400)

    old_priority = thread.priority
    thread.priority = new_priority
    thread.priority_overridden = True
    thread.save(update_fields=["priority", "priority_overridden"])

    _log_activity(
        thread, user, ActivityLog.Action.PRIORITY_CHANGED,
        old_value=old_priority,
        new_value=new_priority,
        detail=f"Priority changed by {user.get_full_name() or user.username}",
    )

    return _render_thread_detail_with_oob_card(thread, request, user)


@login_required
@require_POST
def edit_status(request, pk):
    """Inline edit: change thread status. Admin or assigned user."""
    user = request.user
    can_assign = user.can_assign

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    if not can_assign and thread.assigned_to != user:
        return HttpResponseForbidden("You can only change status on threads assigned to you.")

    new_status = request.POST.get("new_status", "")
    if not new_status:
        return _HttpResponse("Missing new_status.", status=400)

    _change_thread_status(thread, new_status, user)

    return _render_thread_detail_with_oob_card(thread, request, user)


@login_required
@require_GET
def thread_context_menu(request, pk):
    """Return context menu HTML partial with role-aware grouped actions."""
    user = request.user
    can_assign = user.can_assign
    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to"),
        pk=pk,
    )
    denied = _check_member_thread_access(thread, user)
    if denied:
        return denied

    # Can claim: unassigned thread, member has CategoryVisibility (or can_assign)
    can_claim = False
    if thread.assigned_to is None and thread.status != Thread.Status.CLOSED:
        if can_assign:
            can_claim = True
        else:
            # Default-open: if user has NO CategoryVisibility rows, allow all categories
            user_vis = CategoryVisibility.objects.filter(user=user)
            can_claim = not user_vis.exists() or user_vis.filter(category=thread.category).exists()

    # Status actions: only for owner or can_assign
    is_owner_or_assigner = (thread.assigned_to == user or can_assign)
    can_acknowledge = is_owner_or_assigner and thread.status not in (Thread.Status.ACKNOWLEDGED, Thread.Status.CLOSED)
    can_close = is_owner_or_assigner and thread.status != Thread.Status.CLOSED

    context = {
        "thread": thread,
        "can_claim": can_claim,
        "can_acknowledge": can_acknowledge,
        "can_close": can_close,
    }
    return render(request, "emails/_context_menu.html", context)


@login_required
@require_POST
def add_note_view(request, pk):
    """Add an internal note to a thread. Any authenticated user."""
    thread = get_object_or_404(Thread, pk=pk)
    denied = _check_member_thread_access(thread, request.user)
    if denied:
        return denied
    body = (request.POST.get("body") or "").strip()

    if not body:
        # Re-render detail without creating a note
        user = request.user
        can_assign = user.can_assign
        team_members = []
        if can_assign:
            team_members = _get_team_members()
        context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
        return render(request, "emails/_thread_detail.html", context)

    user = request.user

    # Create the note
    note = InternalNote.objects.create(thread=thread, author=user, body=body)

    # Activity log: NOTE_ADDED
    _log_activity(thread, user, ActivityLog.Action.NOTE_ADDED, detail=body[:200])

    # Parse and process @mentions
    usernames = parse_mentions(body)
    for username in usernames:
        mentioned_user = User.objects.filter(username=username, is_active=True).first()
        if mentioned_user:
            note.mentioned_users.add(mentioned_user)
            _log_activity(
                thread, user, ActivityLog.Action.MENTIONED,
                detail=f"Mentioned {mentioned_user.get_full_name() or mentioned_user.username}",
                new_value=mentioned_user.username,
            )
            try:
                _notify_mention(thread, user, mentioned_user)
            except Exception:
                logger.exception("Mention notification failed for %s", mentioned_user.username)

    # Re-render the full detail panel
    can_assign = user.can_assign
    team_members = []
    if can_assign:
        team_members = _get_team_members()

    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    return render(request, "emails/_thread_detail.html", context)


@login_required
@require_POST
def assign_thread_view(request, pk):
    """Assign a thread to a team member. Requires can_assign permission."""
    user = request.user

    if not user.can_assign:
        return HttpResponseForbidden("Only gatekeepers and admins can assign threads to other users.")

    thread = get_object_or_404(Thread, pk=pk)
    assignee_id = request.POST.get("assignee_id")

    if not assignee_id:
        return HttpResponseBadRequest("Please select a team member first.")

    assignee = get_object_or_404(User, pk=assignee_id)
    note = request.POST.get("note", "")

    _assign_thread(thread, assignee, user, note=note)

    # Reset read state for assignee so thread appears unread in their inbox
    ThreadReadState.objects.update_or_create(
        thread=thread, user=assignee,
        defaults={"is_read": False, "read_at": None},
    )

    # Reload with select_related
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = _get_team_members()

    # Primary: updated detail panel
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_html = render_to_string(
        "emails/_thread_detail.html", detail_context, request=request,
    )

    # OOB: update thread card in the list
    card_html = render_to_string(
        "emails/_thread_card.html",
        {"thread": thread, "oob": True},
        request=request,
    )

    response = _HttpResponse(detail_html + card_html)
    response["HX-Trigger"] = "countsChanged"
    return response


@login_required
@require_POST
def change_thread_status_view(request, pk):
    """Change the status of a thread. Admins or assigned user."""
    user = request.user
    can_assign = user.can_assign

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    # Permission: admin or assigned_to user
    if not can_assign and thread.assigned_to != user:
        return HttpResponseForbidden("You can only change status on threads assigned to you.")

    new_status = request.POST.get("new_status", "")
    if not new_status:
        return HttpResponseForbidden("Missing new_status.")

    _change_thread_status(thread, new_status, user)

    # Reload
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)

    team_members = []
    if can_assign:
        team_members = _get_team_members()

    # Primary: updated detail panel
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_html = render_to_string(
        "emails/_thread_detail.html", detail_context, request=request,
    )

    # OOB: update thread card in the list
    card_html = render_to_string(
        "emails/_thread_card.html",
        {"thread": thread, "oob": True},
        request=request,
    )

    response = _HttpResponse(detail_html + card_html)
    response["HX-Trigger"] = "countsChanged"
    return response


@login_required
@require_POST
def claim_thread_view(request, pk):
    """Allow a team member to self-claim an unassigned thread."""
    thread = get_object_or_404(Thread, pk=pk)

    try:
        _claim_thread(thread, request.user)
    except (ValueError, PermissionError) as exc:
        return HttpResponseForbidden(str(exc))

    # Reload with relations
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)

    user = request.user
    can_assign = user.can_assign
    team_members = []
    if can_assign:
        team_members = _get_team_members()

    # Primary: updated detail panel
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_context["toast_msg"] = "Thread claimed"
    detail_html = render_to_string(
        "emails/_thread_detail.html", detail_context, request=request,
    )

    # OOB: update thread card in the list
    card_html = render_to_string(
        "emails/_thread_card.html",
        {"thread": thread, "oob": True},
        request=request,
    )

    response = _HttpResponse(detail_html + card_html)
    response["HX-Trigger"] = "countsChanged"
    return response


@login_required
@require_POST
def reassign_thread_view(request, pk):
    """Member self-reassignment with mandatory reason."""
    user = request.user
    thread = get_object_or_404(Thread, pk=pk)

    # Only members use this endpoint -- admin/gatekeeper use assign endpoint
    if user.can_assign:
        return HttpResponseForbidden("Use the standard assign endpoint instead.")

    if thread.assigned_to != user:
        return HttpResponseForbidden("You can only reassign threads assigned to you.")

    reason = request.POST.get("reason", "").strip()
    if not reason:
        return HttpResponseForbidden("A reason is required when reassigning.")

    assignee_id = request.POST.get("assignee_id")
    if not assignee_id:
        return HttpResponseForbidden("Missing assignee.")

    assignee = get_object_or_404(User, pk=assignee_id, is_active=True)

    try:
        _reassign_thread(thread, assignee, user, reason)
    except (ValueError, PermissionError) as exc:
        return HttpResponseForbidden(str(exc))

    # Reset read state for new assignee
    ThreadReadState.objects.update_or_create(
        thread=thread, user=assignee,
        defaults={"is_read": False, "read_at": None},
    )

    # Reload and return detail + OOB card (standard pattern)
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = []  # Member doesn't get team_members list
    detail_context = _build_thread_detail_context(thread, request, False, team_members)
    detail_html = render_to_string("emails/_thread_detail.html", detail_context, request=request)
    card_html = render_to_string(
        "emails/_thread_card.html", {"thread": thread, "oob": True}, request=request,
    )
    response = _HttpResponse(detail_html + card_html)
    response["HX-Trigger"] = "countsChanged"
    return response


@login_required
@require_POST
def whitelist_sender_from_thread(request, pk):
    """Whitelist the primary sender of a thread. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )
    sender = thread.last_sender_address.strip().lower()

    if not sender:
        return HttpResponseForbidden("Thread has no sender address to whitelist.")

    from django.db import IntegrityError, transaction

    try:
        with transaction.atomic():
            SpamWhitelist.objects.create(
                entry=sender,
                entry_type="email",
                added_by=request.user,
                reason=f"Whitelisted from thread #{pk}",
            )
        updated = _unspam_matching_emails(sender, "email")
        msg = f"{sender} whitelisted"
        if updated:
            msg += f" -- {updated} email(s) unmarked as spam"
    except IntegrityError:
        _unspam_matching_emails(sender, "email")
        msg = f"{sender} is already whitelisted"

    team_members = _get_team_members()

    # Re-render detail panel with feedback banner
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_context["whitelist_msg"] = msg

    return render(request, "emails/_thread_detail.html", detail_context)


@login_required
@require_POST
def mark_spam(request, pk):
    """Mark a thread as spam. All users can do this (no admin restriction)."""
    from django.db import transaction

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )
    denied = _check_member_thread_access(thread, request.user)
    if denied:
        return denied
    sender = (thread.last_sender_address or "").strip().lower()

    with transaction.atomic():
        # Determine original verdict
        original_verdict = any(e.is_spam for e in thread.emails.all())

        # Create feedback
        SpamFeedback.objects.create(
            user=request.user,
            thread=thread,
            original_verdict=original_verdict,
            user_verdict=True,
        )

        # Update all thread emails
        thread.emails.update(is_spam=True)

        # Update sender reputation
        if sender:
            _update_sender_reputation(sender, increment_spam=True)

        # Activity log
        _log_activity(
            thread, request.user, ActivityLog.Action.SPAM_MARKED,
            detail=f"Marked as spam by {request.user.get_full_name() or request.user.username}",
        )

    # Re-render detail panel
    can_assign = request.user.can_assign
    team_members = _get_team_members() if can_assign else []
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_context["toast_msg"] = "Marked as spam"

    return render(request, "emails/_thread_detail.html", detail_context)


@login_required
@require_POST
def mark_not_spam(request, pk):
    """Mark a thread as not spam. All users can do this."""
    from django.db import transaction

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )
    denied = _check_member_thread_access(thread, request.user)
    if denied:
        return denied
    sender = (thread.last_sender_address or "").strip().lower()

    toast_msg = "Marked as not spam"

    with transaction.atomic():
        original_verdict = any(e.is_spam for e in thread.emails.all())

        SpamFeedback.objects.create(
            user=request.user,
            thread=thread,
            original_verdict=original_verdict,
            user_verdict=False,
        )

        thread.emails.update(is_spam=False)

        if sender:
            # Check if sender was blocked before we decrement
            was_blocked = SenderReputation.objects.filter(
                sender_address__iexact=sender, is_blocked=True
            ).exists()

            _update_sender_reputation(sender, decrement_spam=True)

            # Auto-whitelist if sender was blocked (SPAM-05)
            if was_blocked:
                SpamWhitelist.objects.get_or_create(
                    entry=sender,
                    entry_type="email",
                    defaults={
                        "added_by": request.user,
                        "reason": "Auto-whitelisted: user marked not-spam on blocked sender",
                    },
                )

                SenderReputation.objects.filter(sender_address__iexact=sender).update(is_blocked=False)
                toast_msg = "Marked as not spam and sender unblocked"

        _log_activity(
            thread, request.user, ActivityLog.Action.SPAM_UNMARKED,
            detail=f"Marked as not spam by {request.user.get_full_name() or request.user.username}",
        )

    can_assign = request.user.can_assign
    team_members = _get_team_members() if can_assign else []
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_context["toast_msg"] = toast_msg

    return render(request, "emails/_thread_detail.html", detail_context)


@login_required
@require_POST
def mark_irrelevant(request, pk):
    """Mark a thread as irrelevant. Gatekeeper/admin only."""
    from django.db import transaction

    user = request.user
    if not user.can_triage:
        return HttpResponseForbidden("Permission denied.")

    reason = request.POST.get("reason", "").strip()
    if not reason:
        return HttpResponseForbidden("Reason is required.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"), pk=pk
    )

    with transaction.atomic():
        old_status = thread.status
        thread.status = Thread.Status.IRRELEVANT
        thread.save(update_fields=["status", "updated_at"])

        _log_activity(
            thread, user, ActivityLog.Action.MARKED_IRRELEVANT,
            detail=reason,
            old_value=old_status,
            new_value=Thread.Status.IRRELEVANT,
        )

    # Re-render detail panel
    can_assign = user.can_assign
    team_members = _get_team_members() if can_assign else []
    detail_context = _build_thread_detail_context(thread, request, can_assign, team_members)
    detail_context["toast_msg"] = "Thread marked as irrelevant"
    response = render(request, "emails/_thread_detail.html", detail_context)
    response["HX-Trigger"] = "countsChanged"
    return response


@login_required
@require_POST
def revert_irrelevant(request, pk):
    """Revert an irrelevant thread to New status. Gatekeeper/admin only."""
    from django.db import transaction

    user = request.user
    if not user.can_triage:
        return HttpResponseForbidden("Permission denied.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"), pk=pk
    )

    if thread.status != Thread.Status.IRRELEVANT:
        return HttpResponseForbidden("Thread is not marked irrelevant.")

    with transaction.atomic():
        thread.status = Thread.Status.NEW
        thread.assigned_to = None
        thread.assigned_by = None
        thread.assigned_at = None
        thread.save(update_fields=["status", "assigned_to", "assigned_by", "assigned_at", "updated_at"])

        _log_activity(
            thread, user, ActivityLog.Action.REVERTED_IRRELEVANT,
            detail=f"Reverted from irrelevant to new by {user.get_full_name() or user.username}",
            old_value=Thread.Status.IRRELEVANT,
            new_value=Thread.Status.NEW,
        )

    can_assign = user.can_assign
    team_members = _get_team_members() if can_assign else []
    detail_context = _build_thread_detail_context(thread, request, can_assign, team_members)
    detail_context["toast_msg"] = "Thread reverted to New"
    response = render(request, "emails/_thread_detail.html", detail_context)
    response["HX-Trigger"] = "countsChanged"
    return response


@login_required
@require_POST
def undo_spam_feedback(request, pk):
    """Undo a spam feedback action. Reverses reputation change and email spam flag."""
    from django.db import transaction

    fb = get_object_or_404(SpamFeedback, pk=pk)
    thread = fb.thread

    with transaction.atomic():
        sender = ""
        if thread:
            sender = (thread.last_sender_address or "").strip().lower()

        # Reverse reputation change
        if sender:
            if fb.user_verdict:
                # Was marked spam -- undo means decrement spam_count
                _update_sender_reputation(sender, decrement_spam=True)
            else:
                # Was marked not-spam -- undo means increment spam_count
                _update_sender_reputation(sender, increment_spam=True)

        # Reverse email is_spam to original verdict
        if thread:
            thread.emails.update(is_spam=fb.original_verdict)

        # Soft-delete the feedback
        fb.delete()

    # Re-render detail panel
    if thread:
        thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=thread.pk)
        can_assign = request.user.can_assign
        team_members = _get_team_members() if can_assign else []
        detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
        detail_context["toast_msg"] = "Spam feedback undone"
        return render(request, "emails/_thread_detail.html", detail_context)

    return _HttpResponse(status=204)


@login_required
@require_POST
def unblock_sender(request, pk):
    """Unblock a sender (set is_blocked=False). Admin only. Re-renders whitelist tab."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    rep = get_object_or_404(SenderReputation, pk=pk)
    rep.is_blocked = False
    rep.save(update_fields=["is_blocked"])

    return _render_whitelist_tab(
        request, save_success=True,
        save_message=f"{rep.sender_address} unblocked.",
    )


# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------


@login_required
@require_POST
def bulk_assign(request):
    """Bulk assign multiple threads to a user. Requires can_assign permission."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("Permission denied.")

    thread_ids = request.POST.getlist("thread_ids")
    assignee_id = request.POST.get("assignee_id")
    if not thread_ids:
        return _HttpResponse("Missing thread_ids", status=400)
    if not assignee_id:
        return _HttpResponse("Missing assignee_id", status=400)

    from django.urls import reverse

    assignee = get_object_or_404(User, pk=assignee_id, is_active=True)
    threads = Thread.objects.filter(pk__in=thread_ids, status__in=["new", "acknowledged"])

    previous_states = []
    assigned_pks = []
    for thread in threads:
        previous_states.append({
            "thread_id": thread.pk,
            "assigned_to_id": thread.assigned_to_id,
            "status": thread.status,
        })
        thread.assigned_to = assignee
        thread.assigned_by = user
        if thread.status == "new":
            thread.status = "acknowledged"
        thread.save(update_fields=["assigned_to", "assigned_by", "status", "updated_at"])
        _log_activity(
            thread, user, ActivityLog.Action.ASSIGNED,
            email=thread.emails.order_by("-received_at").first(),
            detail=f"Bulk assigned to {assignee.get_full_name() or assignee.username}",
        )
        assigned_pks.append(thread.pk)

    response = _render_thread_list_response(request)
    response["HX-Trigger"] = json.dumps({
        "showUndoToast": {
            "message": f"Assigned {len(assigned_pks)} threads to {assignee.get_full_name() or assignee.username}",
            "undo_url": reverse("emails:bulk_undo"),
            "previous_states": previous_states,
            "action_type": "assign",
        }
    })
    return response


@login_required
@require_POST
def bulk_mark_irrelevant(request):
    """Bulk mark multiple threads as irrelevant. Requires can_triage permission."""
    user = request.user
    if not user.can_triage:
        return HttpResponseForbidden("Permission denied.")

    thread_ids = request.POST.getlist("thread_ids")
    reason = (request.POST.get("reason") or "").strip()
    if not thread_ids:
        return _HttpResponse("Missing thread_ids", status=400)
    if not reason:
        return _HttpResponse("Reason is required", status=400)

    from django.urls import reverse

    threads = Thread.objects.filter(pk__in=thread_ids).exclude(status="irrelevant")

    previous_states = []
    marked_pks = []
    for thread in threads:
        previous_states.append({
            "thread_id": thread.pk,
            "status": thread.status,
            "assigned_to_id": thread.assigned_to_id,
        })
        thread.status = "irrelevant"
        thread.save(update_fields=["status", "updated_at"])
        _log_activity(
            thread, user, ActivityLog.Action.MARKED_IRRELEVANT,
            email=thread.emails.order_by("-received_at").first(),
            detail=f"Bulk marked irrelevant: {reason}",
        )
        marked_pks.append(thread.pk)

    response = _render_thread_list_response(request)
    response["HX-Trigger"] = json.dumps({
        "showUndoToast": {
            "message": f"Marked {len(marked_pks)} threads as irrelevant",
            "undo_url": reverse("emails:bulk_undo"),
            "previous_states": previous_states,
            "action_type": "mark_irrelevant",
        }
    })
    return response


@login_required
@require_POST
def bulk_undo(request):
    """Undo a bulk action by restoring previous thread states."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("Permission denied.")

    try:
        previous_states = json.loads(request.POST.get("previous_states", "[]"))
    except (json.JSONDecodeError, TypeError):
        return _HttpResponse("Invalid undo data", status=400)

    for state in previous_states:
        try:
            thread = Thread.objects.get(pk=state["thread_id"])
            thread.status = state.get("status", thread.status)
            assigned_to_id = state.get("assigned_to_id")
            thread.assigned_to_id = assigned_to_id
            thread.save(update_fields=["status", "assigned_to", "updated_at"])
        except Thread.DoesNotExist:
            continue

    return _render_thread_list_response(request)
