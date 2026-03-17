"""Full-page views: thread list, reports, activity log, dev inspector."""

import json
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    ActivityLog, AssignmentRule, Email, PollLog, Thread, ThreadReadState,
)
from apps.emails.services.dtos import VALID_CATEGORIES, VALID_PRIORITIES

from .helpers import (
    PER_PAGE,
    PRESET_RANGES,
    PRIORITY_EMOJI,
    THREAD_SORT_FIELDS,
    _build_chat_card,
    _get_team_members,
    _member_visible_threads,
    annotate_unread,
)

logger = logging.getLogger(__name__)

PRIORITY_COLOR = {
    "CRITICAL": "#dc2626",
    "HIGH": "#ea580c",
    "MEDIUM": "#ca8a04",
    "LOW": "#16a34a",
}


@login_required
def thread_list(request):
    """Main thread-based dashboard -- three-panel conversation UI."""
    user = request.user
    can_assign = user.can_assign

    # Base queryset — annotate email_count to avoid N+1 on thread.message_count
    # Prefetch emails with only to_inbox + is_spam to avoid N+1 on thread_inbox_badges
    from django.db.models import Count, Exists, OuterRef, Prefetch
    qs = Thread.objects.select_related("assigned_to").prefetch_related(
        Prefetch(
            "emails",
            queryset=Email.objects.only(
                "id", "thread_id", "to_inbox", "is_spam",
                "ai_suggested_assignee", "processing_status", "received_at",
            ),
            to_attr="_prefetched_emails",
        ),
    ).annotate(
        email_count=Count("emails"),
        has_spam=Exists(Email.objects.filter(thread=OuterRef("pk"), is_spam=True)),
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

    # Members can only see their own threads + unclaimed
    if not can_assign and view not in ("mine", "unassigned"):
        view = default_view

    # If an explicit status filter is set, skip view-level status constraints
    # (e.g., ?status=irrelevant should show irrelevant threads regardless of view)
    has_explicit_status = bool(request.GET.get("status", ""))

    if view == "unassigned":
        qs = qs.filter(assigned_to__isnull=True)
        if not has_explicit_status:
            qs = qs.filter(status__in=["new", "acknowledged", "reopened"])
    elif view == "mine":
        qs = qs.filter(assigned_to=user)
    elif view == "all_open":
        if not has_explicit_status:
            qs = qs.filter(status__in=["new", "acknowledged", "reopened"])
    elif view == "closed":
        if not has_explicit_status:
            qs = qs.filter(status__in=["closed", "irrelevant"])
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
    elif not can_assign:
        base_threads = _member_visible_threads(base_threads, user)
    if inbox:
        base_threads = base_threads.filter(emails__to_inbox=inbox).distinct()

    open_q = Q(status__in=["new", "acknowledged", "reopened"])
    sidebar_counts = base_threads.aggregate(
        unassigned=Count("pk", filter=open_q & Q(assigned_to__isnull=True)),
        mine=Count("pk", filter=open_q & Q(assigned_to=user)),
        all_open=Count("pk", filter=open_q),
        closed=Count("pk", filter=Q(status__in=["closed", "irrelevant"])),
        urgent=Count("pk", filter=open_q & Q(priority__in=["CRITICAL", "HIGH"])),
        new=Count("pk", filter=Q(status="new")),
        irrelevant=Count("pk", filter=Q(status="irrelevant")),
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
        assigned_to__isnull=True, status__in=["new", "acknowledged", "reopened"]
    ).count()
    sidebar_counts["unread_open"] = unread_base.filter(
        status__in=["new", "acknowledged", "reopened"]
    ).count()
    sidebar_counts["unread_closed"] = unread_base.filter(
        status__in=["closed", "irrelevant"]
    ).count()

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

    # Compute ai_suggested_assignee_name from prefetched emails (avoids SQLite
    # json_extract bug with KeyTextTransform on TEXT columns).
    for thread in page_obj:
        thread.ai_suggested_assignee_name = None
        for email in getattr(thread, "_prefetched_emails", []):
            if email.processing_status == Email.ProcessingStatus.COMPLETED:
                name = (email.ai_suggested_assignee or {}).get("name", "")
                if name:
                    thread.ai_suggested_assignee_name = name
                    break

    # Team members for assignment dropdown
    team_members = []
    if can_assign:
        team_members = _get_team_members()

    # --- View-scoped stat counts for the stat cards bar ---
    # Must match the exact same filter applied to `qs` above so counts are consistent.
    stat_base = base_threads
    if view == "unassigned":
        stat_base = stat_base.filter(assigned_to__isnull=True, status__in=["new", "acknowledged", "reopened"])
    elif view == "mine":
        stat_base = stat_base.filter(assigned_to=user)
    elif view == "all_open":
        stat_base = stat_base.filter(status__in=["new", "acknowledged", "reopened"])
    elif view == "closed":
        stat_base = stat_base.filter(status__in=["closed", "irrelevant"])
    elif view.isdigit() and is_admin:
        stat_base = stat_base.filter(assigned_to_id=int(view))

    view_stats = stat_base.aggregate(
        total=Count("pk"),
        unassigned_count=Count("pk", filter=Q(assigned_to__isnull=True) & open_q),
        urgent=Count("pk", filter=Q(priority__in=["CRITICAL", "HIGH"])),
        new_count=Count("pk", filter=Q(status="new")),
    )

    # Build current query params (without page) for pagination links
    query_params = request.GET.copy()
    query_params.pop("page", None)

    # --- Corrections digest for gatekeeper/admin on triage queue ---
    corrections_digest = None
    if user.can_triage and view == "unassigned":
        from apps.emails.services.reports import get_corrections_digest
        corrections_digest = get_corrections_digest()

    context = {
        "threads": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "sidebar_counts": sidebar_counts,
        "view_stats": view_stats,
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
        "corrections_digest": corrections_digest,
        "default_view": default_view,
    }

    if getattr(request, "htmx", False):
        context["is_htmx"] = True
        return render(request, "emails/_thread_list_body.html", context)
    return render(request, "emails/thread_list.html", context)


@login_required
def sidebar_counts_view(request):
    """Return sidebar counts partial for HTMX OOB refresh."""
    from django.db.models import Count, Exists, OuterRef, Q

    user = request.user
    can_assign = user.can_assign
    inbox = request.GET.get("inbox", "")
    current_view = request.GET.get("view", "all_open" if can_assign else "mine")
    current_inbox = inbox

    base_threads = Thread.objects.all()
    if user.role == User.Role.TRIAGE_LEAD:
        lead_categories = list(
            AssignmentRule.objects.filter(assignee=user, is_active=True)
            .values_list("category", flat=True)
        )
        if lead_categories:
            base_threads = base_threads.filter(category__in=lead_categories)
        else:
            base_threads = base_threads.none()
    elif not can_assign:
        base_threads = _member_visible_threads(base_threads, user)
    if inbox:
        base_threads = base_threads.filter(emails__to_inbox=inbox).distinct()

    open_q = Q(status__in=["new", "acknowledged", "reopened"])
    sidebar_counts = base_threads.aggregate(
        unassigned=Count("pk", filter=open_q & Q(assigned_to__isnull=True)),
        mine=Count("pk", filter=open_q & Q(assigned_to=user)),
        all_open=Count("pk", filter=open_q),
        closed=Count("pk", filter=Q(status__in=["closed", "irrelevant"])),
        urgent=Count("pk", filter=open_q & Q(priority__in=["CRITICAL", "HIGH"])),
        new=Count("pk", filter=Q(status="new")),
        irrelevant=Count("pk", filter=Q(status="irrelevant")),
    )

    unread_sq = ThreadReadState.objects.filter(
        thread=OuterRef("pk"), user=user,
    ).filter(Q(is_read=False) | Q(read_at__lt=OuterRef("last_message_at")))
    unread_base = base_threads.filter(Exists(unread_sq))
    if inbox:
        unread_base = unread_base.filter(emails__to_inbox=inbox).distinct()
    sidebar_counts["unread_mine"] = unread_base.filter(assigned_to=user).count()
    sidebar_counts["unread_unassigned"] = unread_base.filter(
        assigned_to__isnull=True, status__in=["new", "acknowledged", "reopened"]
    ).count()
    sidebar_counts["unread_open"] = unread_base.filter(
        status__in=["new", "acknowledged", "reopened"]
    ).count()
    sidebar_counts["unread_closed"] = unread_base.filter(
        status__in=["closed", "irrelevant"]
    ).count()

    return render(request, "emails/_sidebar_counts.html", {
        "sidebar_counts": sidebar_counts,
        "current_view": current_view,
        "current_inbox": current_inbox,
    })


@login_required
def reports_view(request):
    """Reports dashboard with aggregated metrics. Requires can_assign."""
    if not request.user.can_assign:
        return HttpResponseForbidden("Access denied.")

    from datetime import datetime as _dt

    from apps.emails.services.reports import (
        get_ai_performance_data,
        get_overview_kpis,
        get_volume_data,
        get_team_data,
        get_sla_data,
    )

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
    ai_perf_data = get_ai_performance_data(start, end, **filters)

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
    active_users = _get_team_members()

    context = {
        "overview_kpis": overview_kpis,
        "volume_data": volume_data,
        "team_data": team_data,
        "sla_data": sla_data,
        "ai_perf_data": ai_perf_data,
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


ACTIVITY_PER_PAGE = 50


@login_required
def activity_log(request):
    """Global activity log -- paginated list of all assignment/status events."""
    user = request.user
    can_assign = user.can_assign

    qs = ActivityLog.objects.select_related("email", "user", "thread").order_by("-created_at")

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

    # Group entries by thread for display
    from collections import OrderedDict
    from django.utils import timezone

    thread_buckets = OrderedDict()
    for log in page_obj:
        key = log.thread_id or 0  # 0 = no thread
        if key not in thread_buckets:
            thread_buckets[key] = {"thread": log.thread, "entries": []}
        thread_buckets[key]["entries"].append(log)

    # Build thread_groups: list of (thread_or_None, entries) sorted by most-recent first
    thread_groups = [
        (bucket["thread"], bucket["entries"])
        for bucket in thread_buckets.values()
    ]

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
        "thread_groups": thread_groups,
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

    # Poll history (last 25, with interval annotations)
    poll_logs = list(PollLog.objects.all()[:25])
    poll_interval_seconds = int(poll_interval) * 60
    for i, log in enumerate(poll_logs):
        if i < len(poll_logs) - 1:
            delta = log.started_at - poll_logs[i + 1].started_at
            secs = int(delta.total_seconds())
            log.interval_seconds = secs
            log.interval_gap = secs > (poll_interval_seconds * 2)
            # Pre-format interval for template
            if secs < 60:
                log.interval_display = f"{secs}s"
            elif secs < 3600:
                m, s = divmod(secs, 60)
                log.interval_display = f"{m}m {s}s" if s else f"{m}m"
            else:
                h, rem = divmod(secs, 3600)
                m = rem // 60
                log.interval_display = f"{h}h {m}m"
        else:
            log.interval_seconds = None
            log.interval_gap = False
            log.interval_display = "--"

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
    """Trigger a single poll cycle. Admin only. Works in all operating modes."""
    if not request.user.is_admin_only:
        return HttpResponseForbidden("Admin access required.")

    import subprocess
    from django.conf import settings

    # Record the latest PollLog ID before running, so we can find the new one
    latest_before = PollLog.objects.order_by('-started_at').values_list('pk', flat=True).first()

    try:
        result = subprocess.run(
            ["python", "manage.py", "run_scheduler", "--once"],
            capture_output=True, text=True, timeout=120,
            cwd=str(settings.BASE_DIR),
        )
        # Try to get the PollLog created during this poll
        poll_log_qs = PollLog.objects.order_by('-started_at')
        if latest_before:
            poll_log_qs = poll_log_qs.exclude(pk=latest_before)
        poll_log = poll_log_qs.first()

        if poll_log:
            return JsonResponse({
                "status": poll_log.status,
                "emails_found": poll_log.emails_found,
                "emails_processed": poll_log.emails_processed,
                "spam_filtered": poll_log.spam_filtered,
                "duration_ms": poll_log.duration_ms,
            })
        else:
            return JsonResponse({
                "status": "ok",
                "emails_found": 0,
                "emails_processed": 0,
                "spam_filtered": 0,
                "duration_ms": 0,
                "output": result.stdout[-500:],
            })
    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Poll timed out after 120s"}, status=504)
