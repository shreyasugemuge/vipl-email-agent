"""Email views: dashboard list + dev inspector.

/emails/         — Main email list dashboard (login required)
/emails/inspect/ — Dev inspector (no login, dev/test only)
"""

import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import Email


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
    """Main email dashboard — card list with filtering, sorting, pagination."""
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

    # --- Counts for filter dropdowns ---
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

    # --- Pagination ---
    paginator = Paginator(qs, PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Team members for admin tabs
    team_members = []
    if is_admin:
        team_members = User.objects.filter(is_active=True).order_by("first_name", "username")

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
    }

    if getattr(request, "htmx", False):
        return render(request, "emails/_email_list_body.html", context)
    return render(request, "emails/email_list.html", context)


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
