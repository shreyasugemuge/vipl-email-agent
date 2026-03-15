"""Email views: dashboard list, detail panel, assignment, status, activity log + dev inspector.

/emails/              -- Thread list dashboard (login required)
/emails/legacy/       -- Legacy email list (kept for backward compatibility)
/emails/<pk>/detail/  -- Email detail panel (HTMX partial)
/emails/<pk>/assign/  -- Assign email (POST, admin only)
/emails/<pk>/status/  -- Change email status (POST)
/emails/activity/     -- Activity log (login required)
/emails/inspect/      -- Dev inspector (no login, dev/test only)
"""

import json
import logging
from datetime import timedelta

import nh3
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
from django.http import HttpResponse as _HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    ActivityLog, AssignmentFeedback, AssignmentRule, CategoryVisibility, Email,
    InternalNote, PollLog, SenderReputation, SLAConfig, SpamFeedback, SpamWhitelist,
    Thread, ThreadReadState, ThreadViewer,
)
from apps.emails.services.dtos import VALID_CATEGORIES, VALID_PRIORITIES
from apps.emails.services.assignment import assign_email as _assign_email
from apps.emails.services.assignment import assign_thread as _assign_thread
from apps.emails.services.assignment import change_status as _change_status
from apps.emails.services.assignment import change_thread_status as _change_thread_status
from apps.emails.services.assignment import claim_email as _claim_email
from apps.emails.services.assignment import claim_thread as _claim_thread
from apps.emails.services.assignment import notify_mention as _notify_mention
from apps.emails.services.assignment import parse_mentions
from apps.emails.services.dtos import VALID_CATEGORIES, VALID_PRIORITIES
from apps.emails.services.reports import (
    get_overview_kpis,
    get_volume_data,
    get_team_data,
    get_sla_data,
)

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Unread annotation helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Thread list dashboard (replaces email_list as default)
# ---------------------------------------------------------------------------

THREAD_SORT_FIELDS = {
    "last_message_at", "-last_message_at",
    "priority", "-priority",
    "status", "-status",
    "subject", "-subject",
    "assigned_to__first_name", "-assigned_to__first_name",
}


@login_required
def thread_list(request):
    """Main thread-based dashboard -- three-panel conversation UI."""
    user = request.user
    can_assign = user.can_assign

    # Base queryset — annotate email_count to avoid N+1 on thread.message_count
    # Prefetch emails with only to_inbox + is_spam to avoid N+1 on thread_inbox_badges
    from django.db.models import Count, Exists, OuterRef, Prefetch, Subquery
    from django.db.models.fields.json import KeyTextTransform
    qs = Thread.objects.select_related("assigned_to").prefetch_related(
        Prefetch("emails", queryset=Email.objects.only("id", "thread_id", "to_inbox", "is_spam"), to_attr="_prefetched_emails"),
    ).annotate(
        email_count=Count("emails"),
        has_spam=Exists(Email.objects.filter(thread=OuterRef("pk"), is_spam=True)),
        ai_suggested_assignee_name=Subquery(
            Email.objects.filter(
                thread=OuterRef("pk"),
                processing_status=Email.ProcessingStatus.COMPLETED,
            ).annotate(
                _suggestion_name=KeyTextTransform("name", "ai_suggested_assignee"),
            ).exclude(_suggestion_name__isnull=True).exclude(_suggestion_name="").order_by("-received_at").values("_suggestion_name")[:1]
        ),
    ).order_by("-last_message_at")

    # Annotate per-user unread state
    qs = annotate_unread(qs, user)

    # --- Category scoping for Triage Lead ---
    lead_categories = []
    if user.role == User.Role.TRIAGE_LEAD:
        lead_categories = list(
            AssignmentRule.objects.filter(
                assignee=user, is_active=True
            ).values_list("category", flat=True)
        )
        if lead_categories:
            qs = qs.filter(category__in=lead_categories)
        else:
            qs = qs.none()

    # --- View filtering (sidebar views) ---
    default_view = "all_open" if can_assign else "mine"
    view = request.GET.get("view", default_view)

    if view == "unassigned":
        qs = qs.filter(assigned_to__isnull=True, status__in=["new", "acknowledged"])
    elif view == "mine":
        qs = qs.filter(assigned_to=user)
    elif view == "all_open":
        qs = qs.filter(status__in=["new", "acknowledged"])
    elif view == "closed":
        qs = qs.filter(status="closed")
    elif view.isdigit():
        # Admin/triage_lead: view specific team member's threads
        if can_assign:
            qs = qs.filter(assigned_to_id=int(view))
        else:
            qs = qs.filter(assigned_to=user)

    # --- Inbox filter ---
    inbox = request.GET.get("inbox", "")
    if inbox:
        qs = qs.filter(emails__to_inbox=inbox).distinct()

    # --- Priority / category / status filters ---
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    if priority:
        qs = qs.filter(priority=priority)
    if category:
        qs = qs.filter(category=category)
    if status_filter:
        qs = qs.filter(status=status_filter)

    # --- Search ---
    search_query = request.GET.get("q", "").strip()
    if search_query:
        from django.db.models import Q
        qs = qs.filter(
            Q(subject__icontains=search_query)
            | Q(ai_summary__icontains=search_query)
            | Q(last_sender__icontains=search_query)
            | Q(last_sender_address__icontains=search_query)
        )

    # --- Sort ---
    sort = request.GET.get("sort", "-last_message_at")
    if sort not in THREAD_SORT_FIELDS:
        sort = "-last_message_at"
    qs = qs.order_by(sort)

    # --- Sidebar counts (single aggregate query instead of 4 separate COUNTs) ---
    from django.db.models import Q
    base_threads = Thread.objects.all()
    # Category scoping for Triage Lead sidebar counts
    if user.role == User.Role.TRIAGE_LEAD:
        if lead_categories:
            base_threads = base_threads.filter(category__in=lead_categories)
        else:
            base_threads = base_threads.none()
    if inbox:
        base_threads = base_threads.filter(emails__to_inbox=inbox).distinct()

    open_q = Q(status__in=["new", "acknowledged"])
    sidebar_counts = base_threads.aggregate(
        unassigned=Count("pk", filter=open_q & Q(assigned_to__isnull=True)),
        mine=Count("pk", filter=open_q & Q(assigned_to=user)),
        all_open=Count("pk", filter=open_q),
        closed=Count("pk", filter=Q(status="closed")),
        urgent=Count("pk", filter=open_q & Q(priority__in=["CRITICAL", "HIGH"])),
        new=Count("pk", filter=Q(status="new")),
    )

    # --- Unread counts for sidebar badges ---
    unread_sq = ThreadReadState.objects.filter(
        thread=OuterRef("pk"), user=user,
    ).filter(Q(is_read=False) | Q(read_at__lt=OuterRef("last_message_at")))
    unread_base = base_threads.filter(Exists(unread_sq))
    if inbox:
        unread_base = unread_base.filter(emails__to_inbox=inbox).distinct()
    sidebar_counts["unread_mine"] = unread_base.filter(assigned_to=user).count()
    sidebar_counts["unread_unassigned"] = unread_base.filter(
        assigned_to__isnull=True, status__in=["new", "acknowledged"]
    ).count()
    sidebar_counts["unread_open"] = unread_base.filter(
        status__in=["new", "acknowledged"]
    ).count()
    sidebar_counts["unread_closed"] = unread_base.filter(status="closed").count()

    # Total unread for browser tab title
    unread_total = sidebar_counts["unread_open"] + sidebar_counts["unread_closed"]

    # --- Inbox list for filter pills ---
    inboxes = list(
        Email.objects.values_list("to_inbox", flat=True)
        .distinct()
        .order_by("to_inbox")
    )
    # Remove empty strings
    inboxes = [i for i in inboxes if i]

    # --- Categories for filter dropdown ---
    categories = list(
        Thread.objects.values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    categories = [c for c in categories if c]

    # --- Pagination ---
    paginator = Paginator(qs, PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Team members for assignment dropdown
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Build current query params (without page) for pagination links
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "threads": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "sidebar_counts": sidebar_counts,
        "current_view": view,
        "current_inbox": inbox,
        "current_priority": priority,
        "current_category": category,
        "current_status": status_filter,
        "current_search": search_query,
        "current_sort": sort,
        "inboxes": inboxes,
        "categories": categories,
        "team_members": team_members,
        "query_params": query_params.urlencode(),
        "statuses": Thread.Status.choices,
        "priorities": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "unread_total": unread_total,
        "lead_categories": lead_categories,
    }

    if getattr(request, "htmx", False):
        return render(request, "emails/_thread_list_body.html", context)
    return render(request, "emails/thread_list.html", context)


# ---------------------------------------------------------------------------
# Email list dashboard (legacy — kept for backward compatibility)
# ---------------------------------------------------------------------------

ALLOWED_SORT_FIELDS = {
    "created_at", "-created_at",
    "priority", "-priority",
    "status", "-status",
    "assigned_to__first_name", "-assigned_to__first_name",
    "from_name", "-from_name",
    "subject", "-subject",
}

PER_PAGE = 25


@login_required
def email_list(request):
    """Main email dashboard -- card list with filtering, sorting, pagination."""
    user = request.user
    can_assign = user.can_assign

    # Base queryset: only completed (triaged) emails
    qs = Email.objects.select_related("assigned_to").filter(
        processing_status=Email.ProcessingStatus.COMPLETED,
    )

    # --- Tab / view param ---
    default_view = "unassigned" if can_assign else "mine"
    view = request.GET.get("view", default_view)

    if view == "all":
        # Can-assign users see all; members without can_see_all_emails see only their own
        if not can_assign and not user.can_see_all_emails:
            qs = qs.filter(assigned_to=user)
    elif view == "unassigned":
        qs = qs.filter(assigned_to__isnull=True)
    elif view == "mine":
        qs = qs.filter(assigned_to=user)
    elif view.isdigit():
        # Can-assign users: view specific team member's emails
        if can_assign:
            qs = qs.filter(assigned_to_id=int(view))
        else:
            qs = qs.filter(assigned_to=user)

    # --- Filters ---
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    inbox = request.GET.get("inbox", "")

    if status:
        qs = qs.filter(status=status)
    if priority:
        if priority == "URGENT":
            qs = qs.filter(priority__in=["CRITICAL", "HIGH"])
        else:
            qs = qs.filter(priority=priority)
    if category:
        qs = qs.filter(category=category)
    if inbox:
        qs = qs.filter(to_inbox=inbox)

    # --- Search ---
    search_query = request.GET.get("q", "").strip()
    if search_query:
        from django.db.models import Q
        qs = qs.filter(
            Q(subject__icontains=search_query)
            | Q(body__icontains=search_query)
            | Q(from_name__icontains=search_query)
            | Q(from_address__icontains=search_query)
            | Q(ai_summary__icontains=search_query)
        )

    # --- Active filter count (for UX-02 filter indicator) ---
    active_filter_count = sum(1 for f in [status, priority, category, inbox, search_query] if f)

    # --- Sort ---
    sort = request.GET.get("sort", "-created_at")
    if sort not in ALLOWED_SORT_FIELDS:
        sort = "-created_at"
    qs = qs.order_by(sort)

    # --- Counts for filter dropdowns + dashboard stats ---
    completed_qs = Email.objects.filter(
        processing_status=Email.ProcessingStatus.COMPLETED,
    )
    categories = list(
        completed_qs.values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    inboxes = list(
        completed_qs.values_list("to_inbox", flat=True)
        .distinct()
        .order_by("to_inbox")
    )

    # Dashboard quick stats (single aggregate query instead of 5 separate COUNTs)
    from django.db.models import Count, Q
    dash_stats = completed_qs.aggregate(
        total=Count("pk"),
        unassigned=Count("pk", filter=Q(assigned_to__isnull=True)),
        critical=Count("pk", filter=Q(priority="CRITICAL")),
        high=Count("pk", filter=Q(priority="HIGH")),
        pending=Count("pk", filter=Q(status="new")),
    )

    # --- Pagination ---
    paginator = Paginator(qs, PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Team members for assignment tabs
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Category visibility for claim button check on cards
    if can_assign:
        user_visible_categories = list(
            Email.objects.values_list("category", flat=True).distinct()
        )
    else:
        user_visible_categories = list(
            CategoryVisibility.objects.filter(user=user).values_list("category", flat=True)
        )

    # Build current query params (without page) for pagination links
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "emails": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "current_view": view,
        "current_status": status,
        "current_priority": priority,
        "current_category": category,
        "current_inbox": inbox,
        "current_sort": sort,
        "categories": categories,
        "inboxes": inboxes,
        "team_members": team_members,
        "statuses": Email.Status.choices,
        "priorities": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "query_params": query_params.urlencode(),
        "dash_stats": dash_stats,
        "user_visible_categories": user_visible_categories,
        "current_search": search_query,
        "active_filter_count": active_filter_count,
    }

    if getattr(request, "htmx", False):
        list_html = render_to_string("emails/_email_list_body.html", context, request=request)
        # OOB swap to update the email count in the tab bar
        count = paginator.count
        plural = "s" if count != 1 else ""
        count_html = (
            f'<span id="email-count" hx-swap-oob="true" '
            f'class="ml-auto text-[11px] font-bold text-slate-400 whitespace-nowrap tabular-nums">'
            f'{count} email{plural}</span>'
        )
        return _HttpResponse(list_html + count_html)
    return render(request, "emails/email_list.html", context)


# ---------------------------------------------------------------------------
# Email detail panel (HTMX partial)
# ---------------------------------------------------------------------------


def _build_detail_context(email, request, can_assign, team_members):
    """Build shared context dict for the email detail partial."""
    sanitized_body_html = ""
    if email.body_html:
        sanitized_body_html = nh3.clean(
            email.body_html,
            tags=SAFE_TAGS,
            attributes=SAFE_ATTRIBUTES,
        )

    # Can this user claim the email?
    can_claim = False
    if email.assigned_to is None:
        if can_assign:
            can_claim = True
        else:
            can_claim = CategoryVisibility.objects.filter(
                user=request.user,
                category=email.category,
            ).exists()

    # AI suggestion dict (if present and non-empty)
    ai_suggestion = None
    suggestion_data = email.ai_suggested_assignee
    if isinstance(suggestion_data, dict) and suggestion_data.get("name"):
        ai_suggestion = suggestion_data

    return {
        "email": email,
        "sanitized_body_html": sanitized_body_html,
        "attachments": email.attachments.all(),
        "activity_logs": email.activity_logs.select_related("user").all()[:20],
        "team_members": team_members,
        "can_claim": can_claim,
        "ai_suggestion": ai_suggestion,
    }


@login_required
def email_detail(request, pk):
    """Return the email detail panel partial for HTMX swap."""
    email = get_object_or_404(
        Email.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    user = request.user
    can_assign = user.can_assign
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    context = _build_detail_context(email, request, request.user.can_assign, team_members)
    return render(request, "emails/_email_detail.html", context)


# ---------------------------------------------------------------------------
# Assignment endpoint (POST, admin only)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def assign_email_view(request, pk):
    """Assign an email to a team member. Requires can_assign permission."""
    user = request.user

    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to assign emails.")

    email = get_object_or_404(Email, pk=pk)
    assignee_id = request.POST.get("assignee_id")

    if not assignee_id:
        return HttpResponseForbidden("Missing assignee_id.")

    assignee = get_object_or_404(User, pk=assignee_id)
    note = request.POST.get("note", "")

    _assign_email(email, assignee, user, note=note)

    # Reload with select_related for template
    email = Email.objects.select_related("assigned_to", "assigned_by").get(pk=pk)

    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated card
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "team_members": team_members},
        request=request,
    )

    # OOB: update detail panel if it's open
    detail_context = _build_detail_context(email, request, True, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )
    oob_detail = (
        f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
    )

    return _HttpResponse(card_html + oob_detail)


# ---------------------------------------------------------------------------
# Claim endpoint (POST)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def claim_email_view(request, pk):
    """Allow a team member to self-claim an unassigned email."""
    email = get_object_or_404(Email, pk=pk)

    try:
        _claim_email(email, request.user)
    except (ValueError, PermissionError) as exc:
        return HttpResponseForbidden(str(exc))

    # Reload with relations
    email = Email.objects.select_related("assigned_to", "assigned_by").get(pk=pk)

    user = request.user
    can_assign = user.can_assign
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated card
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "team_members": team_members},
        request=request,
    )

    # OOB: update detail panel
    detail_context = _build_detail_context(email, request, request.user.can_assign, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )
    oob_detail = (
        f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
    )

    return _HttpResponse(card_html + oob_detail)


# ---------------------------------------------------------------------------
# AI suggestion accept/reject endpoints (POST, requires can_assign)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def accept_ai_suggestion(request, pk):
    """Accept AI suggested assignee -- assigns the email to that user."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to accept AI suggestions.")

    email = get_object_or_404(
        Email.objects.select_related("assigned_to", "assigned_by"), pk=pk,
    )

    suggestion = email.ai_suggested_assignee
    if not isinstance(suggestion, dict) or not suggestion.get("user_id"):
        return HttpResponseForbidden("No valid AI suggestion to accept.")

    assignee = get_object_or_404(User, pk=suggestion["user_id"])
    _assign_email(email, assignee, user, note="Accepted AI suggestion")

    # Reload
    email = Email.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated card
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "team_members": team_members},
        request=request,
    )
    # OOB: update detail panel
    detail_context = _build_detail_context(email, request, True, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )
    oob_detail = (
        f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
    )
    return _HttpResponse(card_html + oob_detail)


@login_required
@require_POST
def reject_ai_suggestion(request, pk):
    """Dismiss AI suggested assignee -- clears the suggestion."""
    user = request.user
    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to dismiss AI suggestions.")

    email = get_object_or_404(
        Email.objects.select_related("assigned_to", "assigned_by"), pk=pk,
    )

    email.ai_suggested_assignee = {}
    email.save(update_fields=["ai_suggested_assignee", "updated_at"])

    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated card (AI badge cleared)
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "team_members": team_members},
        request=request,
    )
    # OOB: update detail panel
    detail_context = _build_detail_context(email, request, True, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )
    oob_detail = (
        f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
    )
    return _HttpResponse(card_html + oob_detail)


# ---------------------------------------------------------------------------
# Thread-level accept/reject AI suggestion (POST)
# ---------------------------------------------------------------------------


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
    if not isinstance(suggestion, dict) or not suggestion.get("user_id"):
        return HttpResponseForbidden("No valid AI suggestion to accept.")

    assignee = get_object_or_404(User, pk=suggestion["user_id"])

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
    ActivityLog.objects.create(
        thread=thread,
        user=user,
        action=ActivityLog.Action.ASSIGNED,
        detail=f"Accepted AI suggestion — assigned to {assignee.get_full_name() or assignee.username}",
    )

    # Re-render detail panel
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    return render(request, "emails/_thread_detail.html", context)


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

    # Re-render detail panel
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    return render(request, "emails/_thread_detail.html", context)


# ---------------------------------------------------------------------------
# Status change endpoint (POST)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def change_status_view(request, pk):
    """Change the status of an email. Admins can change any; members can change their own."""
    user = request.user
    can_assign = user.can_assign

    email = get_object_or_404(
        Email.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    # Permission check: admin or assigned_to user
    if not can_assign and email.assigned_to != user:
        return HttpResponseForbidden("You can only change status on emails assigned to you.")

    new_status = request.POST.get("new_status", "")
    if not new_status:
        return HttpResponseForbidden("Missing new_status.")

    _change_status(email, new_status, user)

    # Reload
    email = Email.objects.select_related("assigned_to", "assigned_by").get(pk=pk)

    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated detail panel
    detail_context = _build_detail_context(email, request, request.user.can_assign, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )

    # OOB: update the card in the list
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "team_members": team_members, "oob": True},
        request=request,
    )

    return _HttpResponse(detail_html + card_html)


# ---------------------------------------------------------------------------
# Thread detail + thread-level action endpoints
# ---------------------------------------------------------------------------


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
    if thread.assigned_to is None:
        if can_assign:
            can_claim = True
        else:
            can_claim = CategoryVisibility.objects.filter(
                user=request.user,
                category=thread.category,
            ).exists()

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
    all_active_users = User.objects.filter(is_active=True).order_by("first_name", "username")
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
    show_suggestion_bar = False
    suggested_assignee_name = ""
    if ai_suggested_assignee and ai_suggested_assignee.get("user_id"):
        if thread.assigned_to is None or thread.is_auto_assigned:
            show_suggestion_bar = True
            suggested_assignee_name = ai_suggested_assignee.get("name", "")

    return {
        "thread": thread,
        "timeline_items": timeline_items,
        "team_members": team_members,
        "team_members_json": team_members_json,
        "can_claim": can_claim,
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


@login_required
@require_POST
def viewer_heartbeat(request, pk):
    """Update viewer presence and return the viewer badge partial."""
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
    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    user = request.user
    can_assign = user.can_assign
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

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
        '<span class="text-sm text-slate-400">Select a thread</span></div>'
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

        ActivityLog.objects.create(
            thread=thread,
            user=user,
            action=ActivityLog.Action.AI_SUMMARY_EDITED,
            old_value=old_summary[:200],
            new_value=new_summary[:200],
            detail=f"AI summary edited by {user.get_full_name() or user.username}",
        )

    # Re-render the detail panel
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    return render(request, "emails/_thread_detail.html", context)


def _render_thread_detail_with_oob_card(thread, request, user):
    """Re-render the detail panel + OOB thread card after an inline edit."""
    can_assign = user.can_assign
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=thread.pk)
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_html = render_to_string("emails/_thread_detail.html", detail_context, request=request)
    card_html = render_to_string("emails/_thread_card.html", {"thread": thread, "oob": True}, request=request)
    return _HttpResponse(detail_html + card_html)


@login_required
@require_POST
def edit_category(request, pk):
    """Inline edit: change thread category. Any logged-in user."""
    user = request.user
    thread = get_object_or_404(Thread, pk=pk)

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

    ActivityLog.objects.create(
        thread=thread,
        user=user,
        action=ActivityLog.Action.CATEGORY_CHANGED,
        old_value=old_category[:200],
        new_value=category[:200],
        detail=f"Category changed by {user.get_full_name() or user.username}",
    )

    return _render_thread_detail_with_oob_card(thread, request, user)


@login_required
@require_POST
def edit_priority(request, pk):
    """Inline edit: change thread priority. Any logged-in user."""
    user = request.user
    thread = get_object_or_404(Thread, pk=pk)

    new_priority = (request.POST.get("priority") or "").strip()
    if new_priority not in VALID_PRIORITIES:
        return _HttpResponse(f"Invalid priority: {new_priority}", status=400)

    old_priority = thread.priority
    thread.priority = new_priority
    thread.priority_overridden = True
    thread.save(update_fields=["priority", "priority_overridden"])

    ActivityLog.objects.create(
        thread=thread,
        user=user,
        action=ActivityLog.Action.PRIORITY_CHANGED,
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

    can_claim = (
        not can_assign
        and thread.assigned_to != user
        and thread.status != Thread.Status.CLOSED
    )
    can_acknowledge = thread.status not in (Thread.Status.ACKNOWLEDGED, Thread.Status.CLOSED)
    can_close = thread.status != Thread.Status.CLOSED

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
    body = (request.POST.get("body") or "").strip()

    if not body:
        # Re-render detail without creating a note
        user = request.user
        can_assign = user.can_assign
        team_members = []
        if can_assign:
            team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
        context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
        return render(request, "emails/_thread_detail.html", context)

    user = request.user

    # Create the note
    note = InternalNote.objects.create(thread=thread, author=user, body=body)

    # Activity log: NOTE_ADDED
    ActivityLog.objects.create(
        thread=thread,
        user=user,
        action=ActivityLog.Action.NOTE_ADDED,
        detail=body[:200],
    )

    # Parse and process @mentions
    usernames = parse_mentions(body)
    for username in usernames:
        mentioned_user = User.objects.filter(username=username, is_active=True).first()
        if mentioned_user:
            note.mentioned_users.add(mentioned_user)
            ActivityLog.objects.create(
                thread=thread,
                user=user,
                action=ActivityLog.Action.MENTIONED,
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
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    return render(request, "emails/_thread_detail.html", context)


@login_required
@require_POST
def assign_thread_view(request, pk):
    """Assign a thread to a team member. Requires can_assign permission."""
    user = request.user

    if not user.can_assign:
        return HttpResponseForbidden("You do not have permission to assign threads.")

    thread = get_object_or_404(Thread, pk=pk)
    assignee_id = request.POST.get("assignee_id")

    if not assignee_id:
        return HttpResponseForbidden("Missing assignee_id.")

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
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

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

    return _HttpResponse(detail_html + card_html)


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
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

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

    return _HttpResponse(detail_html + card_html)


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
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

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

    return _HttpResponse(detail_html + card_html)


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

    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Re-render detail panel with feedback banner
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_context["whitelist_msg"] = msg

    return render(request, "emails/_thread_detail.html", detail_context)


# ---------------------------------------------------------------------------
# Spam feedback: mark spam / not-spam / undo
# ---------------------------------------------------------------------------


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


@login_required
@require_POST
def mark_spam(request, pk):
    """Mark a thread as spam. All users can do this (no admin restriction)."""
    from django.db import transaction

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )
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
        ActivityLog.objects.create(
            thread=thread,
            user=request.user,
            action=ActivityLog.Action.SPAM_MARKED,
            detail=f"Marked as spam by {request.user.get_full_name() or request.user.username}",
        )

    # Re-render detail panel
    can_assign = request.user.can_assign
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username") if can_assign else []
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
                from django.db import IntegrityError
                try:
                    SpamWhitelist.objects.create(
                        entry=sender,
                        entry_type="email",
                        added_by=request.user,
                        reason="Auto-whitelisted: user marked not-spam on blocked sender",
                    )
                except IntegrityError:
                    pass  # Already whitelisted

                SenderReputation.objects.filter(sender_address__iexact=sender).update(is_blocked=False)
                toast_msg = "Marked as not spam and sender unblocked"

        ActivityLog.objects.create(
            thread=thread,
            user=request.user,
            action=ActivityLog.Action.SPAM_UNMARKED,
            detail=f"Marked as not spam by {request.user.get_full_name() or request.user.username}",
        )

    can_assign = request.user.can_assign
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username") if can_assign else []
    detail_context = _build_thread_detail_context(thread, request, request.user.can_assign, team_members)
    detail_context["toast_msg"] = toast_msg

    return render(request, "emails/_thread_detail.html", detail_context)


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
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username") if can_assign else []
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
# Admin settings page
# ---------------------------------------------------------------------------


def _require_admin(user):
    """Return True if user is admin/staff (is_admin_only)."""
    return user.is_admin_only


@login_required
def settings_view(request):
    """Settings page: writable for admins, read-only for triage leads, denied for members."""
    if request.user.is_admin_only:
        readonly = False
    elif request.user.can_triage:
        readonly = True
    else:
        return HttpResponseForbidden("Access denied.")

    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    active_tab = request.GET.get("tab", "rules")

    # Assignment rules grouped by category (list of tuples for template iteration)
    rules_by_category = []
    for cat in VALID_CATEGORIES:
        cat_rules = list(
            AssignmentRule.objects.filter(category=cat, is_active=True)
            .select_related("assignee")
            .order_by("priority_order")
        )
        rules_by_category.append((cat, cat_rules))

    # Category visibility grouped by user
    visibility_by_user = {}
    for member in team_members:
        visibility_by_user[member.pk] = set(
            CategoryVisibility.objects.filter(user=member).values_list("category", flat=True)
        )

    # SLA config as list
    sla_configs = {
        (c.priority, c.category): c
        for c in SLAConfig.objects.all()
    }
    sla_matrix = []
    for priority in VALID_PRIORITIES:
        for category in VALID_CATEGORIES:
            cfg = sla_configs.get((priority, category))
            sla_matrix.append({
                "priority": priority,
                "category": category,
                "ack_hours": cfg.ack_hours if cfg else 1.0,
                "respond_hours": cfg.respond_hours if cfg else 24.0,
                "exists": cfg is not None,
            })

    # Monitored inboxes for Inboxes tab
    raw_inboxes = SystemConfig.get("monitored_inboxes", "") or ""
    if isinstance(raw_inboxes, str):
        monitored_inboxes = [i.strip() for i in raw_inboxes.split(",") if i.strip()]
    else:
        monitored_inboxes = []

    # Config groups for System tab
    all_configs = SystemConfig.objects.all().order_by("category", "key")
    config_groups = {}
    for cfg in all_configs:
        cat = cfg.category or "general"
        config_groups.setdefault(cat, []).append(cfg)

    # Per-category webhook URLs
    category_webhooks = []
    for cat in VALID_CATEGORIES:
        url = SystemConfig.get(f"chat_webhook_{cat.lower()}", "") or ""
        category_webhooks.append({"category": cat, "webhook_url": url})

    # Whitelist entries for Whitelist tab
    whitelist_entries = SpamWhitelist.objects.select_related("added_by").all()

    # Blocked/tracked senders for Whitelist tab
    from django.db.models import Q as _Q2
    blocked_senders = SenderReputation.objects.filter(
        _Q2(spam_count__gt=0) | _Q2(is_blocked=True)
    ).order_by("-is_blocked", "-spam_count")

    context = {
        "active_tab": active_tab,
        "team_members": team_members,
        "rules_by_category": rules_by_category,
        "visibility_by_user": visibility_by_user,
        "sla_matrix": sla_matrix,
        "valid_categories": VALID_CATEGORIES,
        "valid_priorities": VALID_PRIORITIES,
        "monitored_inboxes": monitored_inboxes,
        "config_groups": config_groups,
        "category_webhooks": category_webhooks,
        "whitelist_entries": whitelist_entries,
        "blocked_senders": blocked_senders,
        "readonly": readonly,
    }
    return render(request, "emails/settings.html", context)


@login_required
@require_POST
def settings_rules_save(request):
    """Save assignment rules: add, remove, or reorder."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    action = request.POST.get("action", "")
    category = request.POST.get("category", "")

    if action == "add":
        assignee_id = request.POST.get("assignee_id")
        if assignee_id and category:
            assignee = get_object_or_404(User, pk=assignee_id)
            max_order = (
                AssignmentRule.objects.filter(category=category)
                .order_by("-priority_order")
                .values_list("priority_order", flat=True)
                .first()
            ) or 0
            AssignmentRule.objects.get_or_create(
                category=category,
                assignee=assignee,
                defaults={"priority_order": max_order + 1},
            )

    elif action == "remove":
        assignee_id = request.POST.get("assignee_id")
        if assignee_id and category:
            AssignmentRule.objects.filter(
                category=category, assignee_id=assignee_id,
            ).delete()

    elif action == "reorder":
        assignee_ids = request.POST.getlist("assignee_ids[]")
        for idx, aid in enumerate(assignee_ids):
            AssignmentRule.objects.filter(
                category=category, assignee_id=aid,
            ).update(priority_order=idx)

    # Return partial for the category
    rules = list(
        AssignmentRule.objects.filter(category=category, is_active=True)
        .select_related("assignee")
        .order_by("priority_order")
    )
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    return render(request, "emails/_assignment_rules.html", {
        "category": category,
        "rules": rules,
        "team_members": team_members,
        "save_success": True,
    })


@login_required
@require_POST
def settings_visibility_save(request):
    """Save category visibility for a user (replace all)."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    user_id = request.POST.get("user_id")
    categories = request.POST.getlist("categories[]")

    if user_id:
        target_user = get_object_or_404(User, pk=user_id)
        # Delete existing and recreate
        CategoryVisibility.objects.filter(user=target_user).delete()
        CategoryVisibility.objects.bulk_create([
            CategoryVisibility(user=target_user, category=cat)
            for cat in categories
            if cat in VALID_CATEGORIES
        ])

    # Return updated partial
    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")
    visibility_by_user = {}
    for member in team_members:
        visibility_by_user[member.pk] = set(
            CategoryVisibility.objects.filter(user=member).values_list("category", flat=True)
        )
    return render(request, "emails/_category_visibility.html", {
        "team_members": team_members,
        "visibility_by_user": visibility_by_user,
        "valid_categories": VALID_CATEGORIES,
        "save_success": True,
    })


@login_required
@require_POST
def settings_sla_save(request):
    """Save SLA config for a priority x category pair."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    priority = request.POST.get("priority", "")
    category = request.POST.get("category", "")
    ack_hours = request.POST.get("ack_hours", "1.0")
    respond_hours = request.POST.get("respond_hours", "24.0")

    if priority and category:
        try:
            ack_h = float(ack_hours)
            resp_h = float(respond_hours)
        except (ValueError, TypeError):
            ack_h, resp_h = 1.0, 24.0

        SLAConfig.objects.update_or_create(
            priority=priority,
            category=category,
            defaults={"ack_hours": ack_h, "respond_hours": resp_h},
        )

    # Return updated SLA table partial
    sla_configs = {
        (c.priority, c.category): c
        for c in SLAConfig.objects.all()
    }
    sla_matrix = []
    for p in VALID_PRIORITIES:
        for c in VALID_CATEGORIES:
            cfg = sla_configs.get((p, c))
            sla_matrix.append({
                "priority": p,
                "category": c,
                "ack_hours": cfg.ack_hours if cfg else 1.0,
                "respond_hours": cfg.respond_hours if cfg else 24.0,
                "exists": cfg is not None,
            })

    return render(request, "emails/_sla_config.html", {
        "sla_matrix": sla_matrix,
        "valid_priorities": VALID_PRIORITIES,
        "valid_categories": VALID_CATEGORIES,
        "save_success": True,
    })


@login_required
@require_POST
def settings_inboxes_save(request):
    """Add or remove a monitored inbox email address."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    action = request.POST.get("action", "")
    inbox_email = request.POST.get("inbox_email", "").strip()

    cfg, _created = SystemConfig.objects.get_or_create(
        key="monitored_inboxes",
        defaults={"value": "", "value_type": "str", "category": "email"},
    )
    current = [i.strip() for i in cfg.value.split(",") if i.strip()]

    if action == "add" and inbox_email and inbox_email not in current:
        current.append(inbox_email)
    elif action == "remove" and inbox_email in current:
        current.remove(inbox_email)

    cfg.value = ",".join(current)
    cfg.save(update_fields=["value", "updated_at"])

    return render(request, "emails/_inboxes_tab.html", {
        "monitored_inboxes": current,
        "save_success": True,
    })


@login_required
@require_POST
def settings_config_save(request):
    """Save SystemConfig values for a category group."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    category = request.POST.get("category", "")
    configs_in_cat = SystemConfig.objects.filter(category=category) if category else SystemConfig.objects.none()

    for cfg in configs_in_cat:
        field_name = f"config_{cfg.key}"
        if field_name in request.POST:
            new_val = request.POST.get(field_name, "")
            cfg.value = new_val
            cfg.save(update_fields=["value", "updated_at"])
        elif cfg.value_type == "bool":
            # Unchecked checkbox means false
            cfg.value = "false"
            cfg.save(update_fields=["value", "updated_at"])

    # Rebuild config_groups for full re-render
    all_configs = SystemConfig.objects.all().order_by("category", "key")
    config_groups = {}
    for c in all_configs:
        cat = c.category or "general"
        config_groups.setdefault(cat, []).append(c)

    return render(request, "emails/_config_editor.html", {
        "config_groups": config_groups,
        "save_success": True,
    })


@login_required
@require_POST
def settings_webhooks_save(request):
    """Save per-category Google Chat webhook URLs."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    for cat in VALID_CATEGORIES:
        field_name = f"webhook_{cat.lower()}"
        if field_name in request.POST:
            new_url = request.POST.get(field_name, "").strip()
            config_key = f"chat_webhook_{cat.lower()}"
            SystemConfig.objects.update_or_create(
                key=config_key,
                defaults={
                    "value": new_url,
                    "value_type": "str",
                    "category": "notifications",
                    "description": f"Google Chat webhook for {cat} emails",
                },
            )

    category_webhooks = []
    for cat in VALID_CATEGORIES:
        url = SystemConfig.get(f"chat_webhook_{cat.lower()}", "") or ""
        category_webhooks.append({"category": cat, "webhook_url": url})

    return render(request, "emails/_webhooks_tab.html", {
        "category_webhooks": category_webhooks,
        "save_success": True,
    })


# ---------------------------------------------------------------------------
# Whitelist management
# ---------------------------------------------------------------------------


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


@login_required
@require_POST
def whitelist_add(request):
    """Add a new whitelist entry. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    entry = request.POST.get("entry", "").strip().lower()
    entry_type = request.POST.get("entry_type", "email")

    if not entry:
        return _render_whitelist_tab(
            request, save_error="Entry cannot be empty.",
        )

    if entry_type not in ("email", "domain"):
        entry_type = "email"

    from django.db import IntegrityError, transaction

    try:
        with transaction.atomic():
            SpamWhitelist.objects.create(
                entry=entry,
                entry_type=entry_type,
                added_by=request.user,
            )
        updated = _unspam_matching_emails(entry, entry_type)
        msg = f"{entry} added to whitelist."
        if updated:
            msg += f" {updated} email(s) unmarked as spam."
        return _render_whitelist_tab(
            request, save_success=True, save_message=msg,
        )
    except IntegrityError:
        return _render_whitelist_tab(
            request, save_error=f"{entry} is already whitelisted.",
        )


@login_required
@require_POST
def whitelist_delete(request, pk):
    """Soft-delete a whitelist entry. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    wl = get_object_or_404(SpamWhitelist, pk=pk)
    wl.delete()  # soft delete via SoftDeleteModel
    return _render_whitelist_tab(
        request, save_success=True,
        save_message="Entry removed from whitelist.",
    )


# ---------------------------------------------------------------------------
# Whitelist sender from email detail
# ---------------------------------------------------------------------------


@login_required
@require_POST
def whitelist_sender(request, pk):
    """Whitelist the sender of an email. Admin only. Returns feedback HTML fragment."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    email = get_object_or_404(Email, pk=pk)
    sender = email.from_address.strip().lower()

    from django.db import IntegrityError, transaction

    created = False
    try:
        with transaction.atomic():
            SpamWhitelist.objects.create(
                entry=sender,
                entry_type="email",
                added_by=request.user,
                reason=f"Whitelisted from email #{pk}",
            )
        created = True
        updated = _unspam_matching_emails(sender, "email")
        msg = f"{sender} whitelisted"
        if updated:
            msg += f" — {updated} email(s) unmarked as spam"
    except IntegrityError:
        _unspam_matching_emails(sender, "email")
        msg = f"{sender} is already whitelisted"

    # Reload email (is_spam may have changed)
    email.refresh_from_db()

    can_assign = request.user.can_assign
    team_members = []
    if can_assign:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Re-render detail panel with feedback banner
    detail_context = _build_detail_context(email, request, request.user.can_assign, team_members)
    detail_context["whitelist_msg"] = msg
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )

    # OOB: update ALL cards from this sender (spam tags removed)
    affected_emails = Email.objects.select_related("assigned_to").filter(
        from_address__iexact=sender,
        processing_status=Email.ProcessingStatus.COMPLETED,
    )
    oob_cards = ""
    for affected in affected_emails:
        oob_cards += render_to_string(
            "emails/_email_card.html",
            {"email": affected, "can_assign": can_assign, "team_members": team_members, "oob": True},
            request=request,
        )

    return _HttpResponse(detail_html + oob_cards)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

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


@login_required
def reports_view(request):
    """Reports dashboard with aggregated metrics. Requires can_assign."""
    if not request.user.can_assign:
        return HttpResponseForbidden("Access denied.")

    from datetime import datetime as _dt

    # Parse date range
    preset = request.GET.get("preset", "last_30")
    custom_start = request.GET.get("start")
    custom_end = request.GET.get("end")

    if preset == "custom" and custom_start and custom_end:
        try:
            start = timezone.make_aware(_dt.strptime(custom_start, "%Y-%m-%d"))
            end = timezone.make_aware(_dt.strptime(custom_end, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            ))
        except (ValueError, TypeError):
            start, end = PRESET_RANGES["last_30"]()
    elif preset in PRESET_RANGES:
        start, end = PRESET_RANGES[preset]()
    else:
        start, end = PRESET_RANGES["last_30"]()

    # Parse optional filters
    filters = {}
    inbox_filter = request.GET.get("inbox", "")
    category_filter = request.GET.get("category", "")
    member_filter = request.GET.get("member", "")
    if inbox_filter:
        filters["inbox"] = inbox_filter
    if category_filter:
        filters["category"] = category_filter
    if member_filter:
        try:
            filters["assigned_to"] = int(member_filter)
        except (ValueError, TypeError):
            pass

    # Get all report data
    overview_kpis = get_overview_kpis(start, end, **filters)
    volume_data = get_volume_data(start, end, **filters)
    team_data = get_team_data(start, end, **filters)
    sla_data = get_sla_data(start, end, **filters)

    # Filter dropdown options (SoftDeleteManager already excludes deleted)
    distinct_inboxes = list(
        Email.objects.all()
        .values_list("to_inbox", flat=True)
        .distinct()
        .order_by("to_inbox")
    )
    distinct_categories = list(
        Thread.objects.all()
        .exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    active_users = User.objects.filter(is_active=True).order_by("first_name", "username")

    context = {
        "overview_kpis": overview_kpis,
        "volume_data": volume_data,
        "team_data": team_data,
        "sla_data": sla_data,
        "preset": preset,
        "custom_start": custom_start or "",
        "custom_end": custom_end or "",
        "inbox_filter": inbox_filter,
        "category_filter": category_filter,
        "member_filter": member_filter,
        "distinct_inboxes": distinct_inboxes,
        "distinct_categories": distinct_categories,
        "active_users": active_users,
    }

    return render(request, "emails/reports.html", context)


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

ACTIVITY_PER_PAGE = 50


@login_required
def activity_log(request):
    """Global activity log -- paginated list of all assignment/status events."""
    user = request.user
    can_assign = user.can_assign

    qs = ActivityLog.objects.select_related("email", "user").order_by("-created_at")

    # Non-admin members without can_see_all_emails: own activity or activity on own emails
    if not can_assign and not getattr(user, "can_see_all_emails", False):
        from django.db.models import Q

        qs = qs.filter(Q(user=user) | Q(email__assigned_to=user))

    # Filter by action type
    action_filter = request.GET.get("action", "")
    if action_filter and action_filter in dict(ActivityLog.Action.choices):
        qs = qs.filter(action=action_filter)

    # Filter by date
    date_filter = request.GET.get("date", "")
    if date_filter == "today":
        qs = qs.filter(created_at__date=timezone.localdate())

    paginator = Paginator(qs, ACTIVITY_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Group entries by date for display
    from itertools import groupby
    from django.utils import timezone

    grouped_entries = []
    for date_key, entries in groupby(page_obj, key=lambda e: timezone.localdate(e.created_at)):
        grouped_entries.append((date_key, list(entries)))

    today = timezone.localdate()
    from datetime import timedelta
    yesterday = today - timedelta(days=1)

    # MIS stats
    all_logs = ActivityLog.objects.all()
    if not can_assign and not getattr(user, "can_see_all_emails", False):
        from django.db.models import Q as _Q
        all_logs = all_logs.filter(_Q(user=user) | _Q(email__assigned_to=user))

    mis_stats = {
        "total": all_logs.count(),
        "today": all_logs.filter(created_at__date=today).count(),
        "assignments": all_logs.filter(action__in=["assigned", "reassigned"]).count(),
        "status_changes": all_logs.filter(action__in=["status_changed", "acknowledged", "closed"]).count(),
    }

    context = {
        "page_obj": page_obj,
        "grouped_entries": grouped_entries,
        "total_count": paginator.count,
        "mis_stats": mis_stats,
        "action_filter": action_filter,
        "date_filter": date_filter,
        "action_choices": ActivityLog.Action.choices,
        "today": today,
        "yesterday": yesterday,
    }

    if getattr(request, "htmx", False):
        return render(request, "emails/_activity_feed.html", context)
    return render(request, "emails/activity_log.html", context)


# ---------------------------------------------------------------------------
# Dev inspector
# ---------------------------------------------------------------------------

PRIORITY_EMOJI = {
    "CRITICAL": "\U0001f534",
    "HIGH": "\U0001f7e0",
    "MEDIUM": "\U0001f7e1",
    "LOW": "\U0001f7e2",
}

PRIORITY_COLOR = {
    "CRITICAL": "#dc2626",
    "HIGH": "#ea580c",
    "MEDIUM": "#ca8a04",
    "LOW": "#16a34a",
}


@login_required
@require_GET
def inspect(request):
    """Render the dev inspector page with recent emails and simulated outputs."""
    if not request.user.can_triage:
        return HttpResponseForbidden("Access denied.")
    try:
        count = int(request.GET.get("count", 20))
    except (ValueError, TypeError):
        count = 20
    emails = list(
        Email.objects.order_by("-created_at")[:count]
    )

    # Build simulated Chat card JSON for each email
    for email in emails:
        email.priority_emoji = PRIORITY_EMOJI.get(email.priority, "\u2753")
        email.priority_color = PRIORITY_COLOR.get(email.priority, "#6b7280")
        email.chat_card_json = json.dumps(
            _build_chat_card(email), indent=2, ensure_ascii=False
        )

    # Build summary stats
    stats = {
        "total": len(emails),
        "by_priority": {},
        "by_category": {},
        "by_inbox": {},
    }
    for e in emails:
        stats["by_priority"][e.priority] = stats["by_priority"].get(e.priority, 0) + 1
        stats["by_category"][e.category] = stats["by_category"].get(e.category, 0) + 1
        stats["by_inbox"][e.to_inbox] = stats["by_inbox"].get(e.to_inbox, 0) + 1

    current_mode = SystemConfig.get("operating_mode", "unknown")
    last_poll_epoch = SystemConfig.get("last_poll_epoch", "")
    poll_interval = SystemConfig.get("poll_interval_minutes", "5")

    # Poll history
    poll_logs = PollLog.objects.all()[:50]

    # Pipeline MIS stats (last 7 days)
    from django.db.models import Sum, Avg, Count
    seven_days_ago = timezone.now() - timedelta(days=7)
    pipeline_stats = PollLog.objects.filter(started_at__gte=seven_days_ago).aggregate(
        total_polls=Count("pk"),
        total_found=Sum("emails_found"),
        total_processed=Sum("emails_processed"),
        total_spam=Sum("spam_filtered"),
        avg_duration=Avg("duration_ms"),
    )

    return render(request, "emails/inspect.html", {
        "emails": emails,
        "stats": stats,
        "priority_order": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "current_mode": current_mode,
        "last_poll_epoch": last_poll_epoch,
        "poll_interval_minutes": poll_interval,
        "poll_logs": poll_logs,
        "pipeline_stats": pipeline_stats,
    })


@login_required
@require_POST
def force_poll(request):
    """Trigger a single poll cycle. Admin only."""
    if not request.user.is_admin_only:
        return HttpResponseForbidden("Admin access required.")

    import subprocess
    from django.conf import settings
    try:
        result = subprocess.run(
            ["python", "manage.py", "run_scheduler", "--once"],
            capture_output=True, text=True, timeout=120,
            cwd=str(settings.BASE_DIR),
        )
        return JsonResponse({
            "status": "ok",
            "output": result.stdout[-500:],
            "errors": result.stderr[-500:],
        })
    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Poll timed out after 120s"}, status=504)


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
