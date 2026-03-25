"""Shared constants, utilities, and internal helpers for email views."""

import json
import logging
from datetime import timedelta

import nh3
from django.http import HttpResponseForbidden
from django.http import HttpResponse as _HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    ActivityLog, AssignmentFeedback, AssignmentRule, CategoryVisibility, Email,
    InternalNote, PollLog, SenderReputation, SLAConfig, SpamFeedback, SpamWhitelist,
    Thread, ThreadReadState, ThreadViewer,
)
from apps.emails.services.dtos import VALID_CATEGORIES, VALID_PRIORITIES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DRY helpers
# ---------------------------------------------------------------------------


def _get_team_members():
    """Return active users ordered by first_name, username.

    Centralises the repeated ``User.objects.filter(is_active=True).order_by(...)``
    query used across views/templates for assignment dropdowns, settings pages, etc.
    """
    return User.objects.filter(is_active=True).order_by("first_name", "username")


def _log_activity(thread, user, action, *, email=None, old_value=None,
                  new_value=None, detail=""):
    """Create an ActivityLog entry — thin wrapper around ``ActivityLog.objects.create``.

    All keyword arguments after *action* are optional and mirror the model fields.
    """
    kwargs = {"thread": thread, "user": user, "action": action}
    if email is not None:
        kwargs["email"] = email
    if old_value is not None:
        kwargs["old_value"] = old_value
    if new_value is not None:
        kwargs["new_value"] = new_value
    if detail:
        kwargs["detail"] = detail
    return ActivityLog.objects.create(**kwargs)


# Allowed HTML tags for body_html sanitization
SAFE_TAGS = {
    "p", "br", "strong", "em", "ul", "ol", "li", "a",
    "h1", "h2", "h3", "h4", "table", "tr", "td", "th",
    "thead", "tbody", "span", "div", "blockquote",
}
SAFE_ATTRIBUTES = {
    "a": {"href"},
    "span": set(),
    "td": {"colspan", "rowspan"},
}

PER_PAGE = 25

THREAD_SORT_FIELDS = {
    "last_message_at", "-last_message_at",
    "priority", "-priority",
    "status", "-status",
    "subject", "-subject",
    "assigned_to__first_name", "-assigned_to__first_name",
}

PRIORITY_EMOJI = {
    "CRITICAL": "\U0001f534",
    "HIGH": "\U0001f7e0",
    "MEDIUM": "\U0001f7e1",
    "LOW": "\U0001f7e2",
}

PRESET_RANGES = {
    "today": lambda: (timezone.now().replace(hour=0, minute=0, second=0, microsecond=0), timezone.now()),
    "this_week": lambda: (
        timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=timezone.now().weekday()),
        timezone.now(),
    ),
    "this_month": lambda: (
        timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        timezone.now(),
    ),
    "last_7": lambda: (timezone.now() - timedelta(days=7), timezone.now()),
    "last_30": lambda: (timezone.now() - timedelta(days=30), timezone.now()),
    "last_90": lambda: (timezone.now() - timedelta(days=90), timezone.now()),
    "quarter": lambda: (timezone.now() - timedelta(days=90), timezone.now()),
    "year": lambda: (timezone.now() - timedelta(days=365), timezone.now()),
}


# ---------------------------------------------------------------------------
# Unread annotation helper
# ---------------------------------------------------------------------------


def _member_visible_threads(qs, user):
    """Restrict queryset to threads a member can see: assigned-to-them OR unassigned."""
    from django.db.models import Q
    return qs.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))


def _check_member_thread_access(thread, user):
    """Return HttpResponseForbidden if a non-admin member shouldn't access this thread."""
    if not user.can_assign and thread.assigned_to is not None and thread.assigned_to != user:
        return HttpResponseForbidden("Access denied.")
    return None


def annotate_unread(qs, user):
    """Annotate thread queryset with is_unread boolean for the given user.

    No ThreadReadState row = treated as read (avoids wall-of-bold on first deploy).
    Unread when: is_read=False OR read_at < last_message_at (new message since read).
    """
    from django.db.models import Exists, OuterRef, Q

    unread_sq = ThreadReadState.objects.filter(
        thread=OuterRef("pk"), user=user,
    ).filter(Q(is_read=False) | Q(read_at__lt=OuterRef("last_message_at")))
    return qs.annotate(is_unread=Exists(unread_sq))


def _resolve_user_by_name(full_name: str):
    """Resolve a User from a full name like 'Jyotsna Ugemuge'.

    Strategy:
    1. Try first_name + last_name exact match (case-insensitive)
    2. Try first_name only (handles single-name suggestions like 'Aniket')
    3. Try username icontains as fallback
    """
    from django.db.models import Q

    parts = full_name.strip().split()
    if not parts:
        return None

    first = parts[0]
    last = parts[-1] if len(parts) > 1 else None

    # 1. Exact first+last match
    if last:
        user = User.objects.filter(
            first_name__iexact=first, last_name__iexact=last, is_active=True,
        ).first()
        if user:
            return user

    # 2. First name only
    user = User.objects.filter(first_name__iexact=first, is_active=True).first()
    if user:
        return user

    # 3. Username fallback
    return User.objects.filter(username__iexact=first, is_active=True).first()


def _build_thread_detail_context(thread, request, can_assign, team_members):
    """Build context dict for the thread detail partial."""

    # Load all emails in the thread, oldest first
    emails = (
        thread.emails
        .select_related("assigned_to")
        .prefetch_related("attachments")
        .order_by("received_at")
    )

    # Pre-sanitize each email body and attach to the object
    for email in emails:
        if email.body_html:
            email.sanitized_body_html = nh3.clean(
                email.body_html,
                tags=SAFE_TAGS,
                attributes=SAFE_ATTRIBUTES,
            )
        else:
            email.sanitized_body_html = ""

    # Load thread activity logs (chronological, oldest first)
    activity_logs = (
        thread.activity_logs
        .select_related("user", "email")
        .order_by("created_at")
    )

    # Load internal notes
    notes = (
        thread.notes
        .select_related("author")
        .prefetch_related("mentioned_users")
        .order_by("created_at")
    )

    # Build merged timeline: messages + activity events + notes interleaved by timestamp
    timeline_items = []
    for email in emails:
        timeline_items.append({
            "type": "message",
            "timestamp": email.received_at,
            "obj": email,
        })
    for log in activity_logs:
        timeline_items.append({
            "type": "activity",
            "timestamp": log.created_at,
            "obj": log,
        })
    for note in notes:
        timeline_items.append({
            "type": "note",
            "timestamp": note.created_at,
            "obj": note,
        })
    timeline_items.sort(key=lambda x: x["timestamp"])

    # Can this user claim?
    can_claim = False
    claim_disabled = False
    if thread.assigned_to is None:
        if can_assign:
            can_claim = True
        else:
            # Default-open: if user has NO CategoryVisibility rows, allow all categories
            user_vis = CategoryVisibility.objects.filter(user=request.user)
            if user_vis.exists():
                has_visibility = user_vis.filter(category=thread.category).exists()
                if has_visibility:
                    can_claim = True
                else:
                    claim_disabled = True
            else:
                can_claim = True

    # Reassign candidates (category-filtered active users for member reassign form)
    reassign_candidates = []
    if not can_assign and thread.assigned_to == request.user:
        reassign_candidates = User.objects.filter(
            is_active=True,
            pk__in=CategoryVisibility.objects.filter(
                category=thread.category,
            ).values_list("user_id", flat=True),
        ).exclude(pk=request.user.pk).order_by("first_name", "username")

    # AI suggested assignee from the latest completed email
    ai_suggested_assignee = None
    latest_completed = (
        thread.emails
        .filter(processing_status=Email.ProcessingStatus.COMPLETED)
        .order_by("-received_at")
        .first()
    )
    if latest_completed:
        suggestion = latest_completed.ai_suggested_assignee
        if isinstance(suggestion, dict) and suggestion.get("name"):
            ai_suggested_assignee = suggestion

    # AI reasoning from latest completed email
    ai_reasoning = ""
    if latest_completed and latest_completed.ai_reasoning:
        ai_reasoning = latest_completed.ai_reasoning

    # Build team members JSON for @mention autocomplete
    all_active_users = _get_team_members()
    team_members_json = json.dumps([
        {
            "username": u.username,
            "name": u.get_full_name() or u.username,
            "initial": (u.first_name[:1] if u.first_name else u.username[:1]).upper(),
        }
        for u in all_active_users
    ])

    # Check if any email in the thread is spam
    has_spam = any(e.is_spam for e in emails)

    # Determine if suggestion bar should show:
    # (1) unassigned thread with valid ai_suggested_assignee, or (2) auto-assigned thread
    # Show bar if AI suggested a name — user_id is optional (resolve on accept)
    show_suggestion_bar = False
    suggested_assignee_name = ""
    if ai_suggested_assignee and ai_suggested_assignee.get("name"):
        if thread.assigned_to is None or thread.is_auto_assigned:
            show_suggestion_bar = True
            suggested_assignee_name = ai_suggested_assignee.get("name", "")

    return {
        "thread": thread,
        "timeline_items": timeline_items,
        "team_members": team_members,
        "team_members_json": team_members_json,
        "can_claim": can_claim,
        "claim_disabled": claim_disabled,
        "reassign_candidates": reassign_candidates,
        "ai_suggested_assignee": ai_suggested_assignee,
        "ai_reasoning": ai_reasoning,
        "categories": VALID_CATEGORIES,
        "priorities": VALID_PRIORITIES,
        "statuses": Thread.Status.choices,
        "has_spam": has_spam,
        "show_suggestion_bar": show_suggestion_bar,
        "suggested_assignee_name": suggested_assignee_name,
    }


def get_active_viewers(thread_pk, exclude_user_id=None):
    """Return ThreadViewer queryset for viewers active within the last 30 seconds."""
    cutoff = timezone.now() - timedelta(seconds=30)
    qs = ThreadViewer.objects.filter(thread_id=thread_pk, last_seen__gte=cutoff).select_related("user")
    if exclude_user_id is not None:
        qs = qs.exclude(user_id=exclude_user_id)
    return qs


def _render_thread_detail_with_oob_card(thread, request, user):
    """Re-render the detail panel + OOB thread card after an inline edit."""
    can_assign = user.can_assign
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=thread.pk)
    team_members = []
    if can_assign:
        team_members = _get_team_members()
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_html = render_to_string("emails/_thread_detail.html", detail_context, request=request)
    card_html = render_to_string("emails/_thread_card.html", {"thread": thread, "oob": True}, request=request)
    return _HttpResponse(detail_html + card_html)


def _render_thread_list_response(request):
    """Re-render the thread list body partial for HTMX bulk action responses.

    Reuses the same filtering/pagination/sidebar logic from thread_list view
    by delegating to it with an HTMX request marker.
    """
    # Import here to avoid circular import
    from .pages import thread_list

    # Build a minimal HTMX-like request so thread_list returns the partial
    class _FakeHtmx:
        def __bool__(self):
            return True
    original_htmx = getattr(request, "htmx", None)
    request.htmx = _FakeHtmx()
    try:
        return thread_list(request)
    finally:
        request.htmx = original_htmx


def _update_sender_reputation(sender_address, increment_spam=False, decrement_spam=False):
    """Update SenderReputation for a sender. Returns the updated object.

    Uses F() expressions for atomic updates, then refresh_from_db before
    checking auto-block threshold (Pitfall 1 from research).
    """
    from django.db.models import F
    from django.db.models.functions import Greatest

    rep, created = SenderReputation.objects.get_or_create(
        sender_address=sender_address.lower(),
        defaults={"total_count": 0, "spam_count": 0},
    )

    update_fields = {}
    if increment_spam:
        update_fields["spam_count"] = F("spam_count") + 1
    if decrement_spam:
        update_fields["spam_count"] = Greatest(F("spam_count") - 1, 0)

    if update_fields:
        SenderReputation.objects.filter(pk=rep.pk).update(**update_fields)
        rep.refresh_from_db()

    # Auto-block threshold: ratio > 0.8 AND total >= 3
    if rep.total_count >= 3 and rep.spam_ratio > 0.8:
        if not rep.is_blocked:
            rep.is_blocked = True
            rep.save(update_fields=["is_blocked"])
    else:
        if rep.is_blocked:
            # Re-check: maybe undo brought ratio back down
            rep.is_blocked = False
            rep.save(update_fields=["is_blocked"])

    return rep


def _require_admin(user):
    """Return True if user is admin/staff (is_admin_only)."""
    return user.is_admin_only


def _render_whitelist_tab(request, save_success=False, save_message="", save_error=""):
    """Render the whitelist tab partial with current entries and blocked senders."""
    from django.db.models import Q as _Q3
    entries = SpamWhitelist.objects.select_related("added_by").all()
    blocked = SenderReputation.objects.filter(
        _Q3(spam_count__gt=0) | _Q3(is_blocked=True)
    ).order_by("-is_blocked", "-spam_count")
    return render(request, "emails/_whitelist_tab.html", {
        "whitelist_entries": entries,
        "blocked_senders": blocked,
        "save_success": save_success,
        "save_message": save_message,
        "save_error": save_error,
    })


def _unspam_matching_emails(entry: str, entry_type: str) -> int:
    """Mark existing spam emails as not-spam when their sender matches a new whitelist entry."""
    if entry_type == "email":
        qs = Email.objects.filter(is_spam=True, from_address__iexact=entry)
    else:  # domain
        qs = Email.objects.filter(is_spam=True, from_address__iendswith=f"@{entry}")
    return qs.update(is_spam=False)


def _build_chat_card(email):
    """Build the Google Chat Cards v2 payload that *would* be sent."""
    pri = email.priority or "MEDIUM"
    emoji = PRIORITY_EMOJI.get(pri, "\u2753")
    return {
        "cardsV2": [{
            "cardId": f"email-{email.pk}",
            "card": {
                "header": {
                    "title": f"{emoji} {pri}: {email.subject[:60]}",
                    "subtitle": f"{email.category} \u2192 {email.ai_suggested_assignee or 'Unassigned'}",
                },
                "sections": [{
                    "widgets": [
                        {"decoratedText": {"topLabel": "From", "text": f"{email.from_name} <{email.from_address}>"}},
                        {"decoratedText": {"topLabel": "Inbox", "text": email.to_inbox}},
                        {"decoratedText": {"topLabel": "Summary", "text": email.ai_summary or "(none)"}},
                    ]
                }]
            }
        }]
    }
