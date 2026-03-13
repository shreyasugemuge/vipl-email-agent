"""Email views: dashboard list, detail panel, assignment, status, activity log + dev inspector.

/emails/              -- Main email list dashboard (login required)
/emails/<pk>/detail/  -- Email detail panel (HTMX partial)
/emails/<pk>/assign/  -- Assign email (POST, admin only)
/emails/<pk>/status/  -- Change email status (POST)
/emails/activity/     -- Activity log (login required)
/emails/inspect/      -- Dev inspector (no login, dev/test only)
"""

import json
import logging

import nh3
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
from django.http import HttpResponse as _HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    ActivityLog, AssignmentRule, CategoryVisibility, Email, SLAConfig,
)
from apps.emails.services.assignment import assign_email as _assign_email
from apps.emails.services.assignment import change_status as _change_status
from apps.emails.services.assignment import claim_email as _claim_email
from apps.emails.services.dtos import VALID_CATEGORIES, VALID_PRIORITIES

logger = logging.getLogger(__name__)

# Allowed HTML tags for body_html sanitization
SAFE_TAGS = {
    "p", "br", "strong", "em", "ul", "ol", "li", "a",
    "h1", "h2", "h3", "h4", "table", "tr", "td", "th",
    "thead", "tbody", "span", "div", "blockquote",
}
SAFE_ATTRIBUTES = {
    "a": {"href"},
    "span": {"style"},
    "td": {"colspan", "rowspan"},
}


# ---------------------------------------------------------------------------
# Email list dashboard
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
    is_admin = user.is_staff or user.role == User.Role.ADMIN

    # Base queryset: only completed (triaged) emails
    qs = Email.objects.select_related("assigned_to").filter(
        processing_status=Email.ProcessingStatus.COMPLETED,
    )

    # --- Tab / view param ---
    default_view = "unassigned" if is_admin else "mine"
    view = request.GET.get("view", default_view)

    if view == "all":
        # Admin sees all; members without can_see_all_emails see only their own
        if not is_admin and not user.can_see_all_emails:
            qs = qs.filter(assigned_to=user)
    elif view == "unassigned":
        qs = qs.filter(assigned_to__isnull=True)
    elif view == "mine":
        qs = qs.filter(assigned_to=user)
    elif view.isdigit():
        # Admin-only: view specific team member's emails
        if is_admin:
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
        qs = qs.filter(priority=priority)
    if category:
        qs = qs.filter(category=category)
    if inbox:
        qs = qs.filter(to_inbox=inbox)

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

    # Dashboard quick stats
    dash_stats = {
        "total": completed_qs.count(),
        "unassigned": completed_qs.filter(assigned_to__isnull=True).count(),
        "critical": completed_qs.filter(priority="CRITICAL").count(),
        "high": completed_qs.filter(priority="HIGH").count(),
        "pending": completed_qs.filter(status="new").count(),
    }

    # --- Pagination ---
    paginator = Paginator(qs, PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Team members for admin tabs
    team_members = []
    if is_admin:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Category visibility for claim button check on cards
    if is_admin:
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
        "is_admin": is_admin,
        "statuses": Email.Status.choices,
        "priorities": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "query_params": query_params.urlencode(),
        "dash_stats": dash_stats,
        "user_visible_categories": user_visible_categories,
    }

    if getattr(request, "htmx", False):
        return render(request, "emails/_email_list_body.html", context)
    return render(request, "emails/email_list.html", context)


# ---------------------------------------------------------------------------
# Email detail panel (HTMX partial)
# ---------------------------------------------------------------------------


def _build_detail_context(email, request, is_admin, team_members):
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
        if is_admin:
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
        "is_admin": is_admin,
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
    is_admin = user.is_staff or user.role == User.Role.ADMIN
    team_members = []
    if is_admin:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    context = _build_detail_context(email, request, is_admin, team_members)
    return render(request, "emails/_email_detail.html", context)


# ---------------------------------------------------------------------------
# Assignment endpoint (POST, admin only)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def assign_email_view(request, pk):
    """Assign an email to a team member. Admin only."""
    user = request.user
    is_admin = user.is_staff or user.role == User.Role.ADMIN

    if not is_admin:
        return HttpResponseForbidden("Only admins can assign emails.")

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
        {"email": email, "is_admin": is_admin, "team_members": team_members},
        request=request,
    )

    # OOB: update detail panel if it's open
    detail_context = _build_detail_context(email, request, is_admin, team_members)
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
    is_admin = user.is_staff or user.role == User.Role.ADMIN
    team_members = []
    if is_admin:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated card
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "is_admin": is_admin, "team_members": team_members},
        request=request,
    )

    # OOB: update detail panel
    detail_context = _build_detail_context(email, request, is_admin, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )
    oob_detail = (
        f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
    )

    return _HttpResponse(card_html + oob_detail)


# ---------------------------------------------------------------------------
# AI suggestion accept/reject endpoints (POST, admin only)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def accept_ai_suggestion(request, pk):
    """Accept AI suggested assignee -- assigns the email to that user."""
    user = request.user
    is_admin = user.is_staff or user.role == User.Role.ADMIN
    if not is_admin:
        return HttpResponseForbidden("Only admins can accept AI suggestions.")

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
        {"email": email, "is_admin": is_admin, "team_members": team_members},
        request=request,
    )
    # OOB: update detail panel
    detail_context = _build_detail_context(email, request, is_admin, team_members)
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
    is_admin = user.is_staff or user.role == User.Role.ADMIN
    if not is_admin:
        return HttpResponseForbidden("Only admins can dismiss AI suggestions.")

    email = get_object_or_404(
        Email.objects.select_related("assigned_to", "assigned_by"), pk=pk,
    )

    email.ai_suggested_assignee = {}
    email.save(update_fields=["ai_suggested_assignee", "updated_at"])

    team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated card (AI badge cleared)
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "is_admin": is_admin, "team_members": team_members},
        request=request,
    )
    # OOB: update detail panel
    detail_context = _build_detail_context(email, request, is_admin, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )
    oob_detail = (
        f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
    )
    return _HttpResponse(card_html + oob_detail)


# ---------------------------------------------------------------------------
# Status change endpoint (POST)
# ---------------------------------------------------------------------------


@login_required
@require_POST
def change_status_view(request, pk):
    """Change the status of an email. Admins can change any; members can change their own."""
    user = request.user
    is_admin = user.is_staff or user.role == User.Role.ADMIN

    email = get_object_or_404(
        Email.objects.select_related("assigned_to", "assigned_by"),
        pk=pk,
    )

    # Permission check: admin or assigned_to user
    if not is_admin and email.assigned_to != user:
        return HttpResponseForbidden("You can only change status on emails assigned to you.")

    new_status = request.POST.get("new_status", "")
    if not new_status:
        return HttpResponseForbidden("Missing new_status.")

    _change_status(email, new_status, user)

    # Reload
    email = Email.objects.select_related("assigned_to", "assigned_by").get(pk=pk)

    team_members = []
    if is_admin:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

    # Primary: updated detail panel
    detail_context = _build_detail_context(email, request, is_admin, team_members)
    detail_html = render_to_string(
        "emails/_email_detail.html", detail_context, request=request,
    )

    # OOB: update the card in the list
    card_html = render_to_string(
        "emails/_email_card.html",
        {"email": email, "is_admin": is_admin, "team_members": team_members, "oob": True},
        request=request,
    )

    return _HttpResponse(detail_html + card_html)


# ---------------------------------------------------------------------------
# Admin settings page
# ---------------------------------------------------------------------------


def _require_admin(user):
    """Return True if user is admin/staff."""
    return user.is_staff or user.role == User.Role.ADMIN


@login_required
def settings_view(request):
    """Admin settings page with tabs for rules, visibility, SLA config."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

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


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

ACTIVITY_PER_PAGE = 50


@login_required
def activity_log(request):
    """Global activity log -- paginated list of all assignment/status events."""
    user = request.user
    is_admin = user.is_staff or user.role == User.Role.ADMIN

    qs = ActivityLog.objects.select_related("email", "user").order_by("-created_at")

    # Non-admin members without can_see_all_emails: own activity or activity on own emails
    if not is_admin and not getattr(user, "can_see_all_emails", False):
        from django.db.models import Q

        qs = qs.filter(Q(user=user) | Q(email__assigned_to=user))

    # Filter by action type
    action_filter = request.GET.get("action", "")
    if action_filter and action_filter in dict(ActivityLog.Action.choices):
        qs = qs.filter(action=action_filter)

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
    if not is_admin and not getattr(user, "can_see_all_emails", False):
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


@require_GET
def inspect(request):
    """Render the dev inspector page with recent emails and simulated outputs."""
    count = int(request.GET.get("count", 20))
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

    return render(request, "emails/inspect.html", {
        "emails": emails,
        "stats": stats,
        "priority_order": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "current_mode": current_mode,
    })


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
