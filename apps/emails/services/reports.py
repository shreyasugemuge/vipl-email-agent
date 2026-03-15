"""Reports aggregation service for VIPL Email Agent.

Provides data for the Reports dashboard: overview KPIs, email volume,
team performance, and SLA compliance metrics.

All functions accept start_date, end_date (datetime), and optional
filter kwargs (inbox, category, assigned_to).
"""

import logging
from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.emails.models import ActivityLog, Email, Thread

logger = logging.getLogger(__name__)

# Chart colors per inbox
INBOX_COLORS = {
    "info@vidarbhainfotech.com": "#a83362",
    "sales@vidarbhainfotech.com": "#3b82f6",
}
DEFAULT_INBOX_COLOR = "#10b981"


def _apply_filters(qs, model, **filters):
    """Apply optional filters to a queryset. DRY helper for all report functions.

    Args:
        qs: The queryset to filter.
        model: 'email', 'thread', or 'activity' -- determines field mapping.
        **filters: Optional filters: inbox, category, assigned_to.
    """
    inbox = filters.get("inbox")
    category = filters.get("category")
    assigned_to = filters.get("assigned_to")

    if inbox:
        if model == "email":
            qs = qs.filter(to_inbox=inbox)
        elif model == "thread":
            qs = qs.filter(emails__to_inbox=inbox).distinct()
        elif model == "activity":
            qs = qs.filter(
                Q(thread__emails__to_inbox=inbox) | Q(email__to_inbox=inbox)
            ).distinct()

    if category:
        if model == "email":
            qs = qs.filter(thread__category=category)
        elif model == "thread":
            qs = qs.filter(category=category)
        elif model == "activity":
            qs = qs.filter(
                Q(thread__category=category) | Q(email__category=category)
            )

    if assigned_to:
        if model == "email":
            qs = qs.filter(thread__assigned_to_id=assigned_to)
        elif model == "thread":
            qs = qs.filter(assigned_to_id=assigned_to)
        elif model == "activity":
            qs = qs.filter(
                Q(thread__assigned_to_id=assigned_to) | Q(email__assigned_to_id=assigned_to)
            )

    return qs


def get_overview_kpis(start, end, **filters):
    """Overview KPI cards: total emails, avg response, SLA compliance, open threads.

    Args:
        start: Start datetime (inclusive).
        end: End datetime (inclusive).
        **filters: Optional inbox, category, assigned_to.

    Returns:
        dict with total_emails, avg_response_minutes, sla_compliance_pct, open_threads.
    """
    # Total non-spam emails received in period
    # SoftDeleteManager already excludes deleted_at != NULL
    email_qs = Email.objects.filter(
        is_spam=False, received_at__gte=start, received_at__lte=end,
    )
    email_qs = _apply_filters(email_qs, "email", **filters)
    total_emails = email_qs.count()

    # Avg response time: thread created_at -> first ACKNOWLEDGED activity
    thread_qs = Thread.objects.filter(
        created_at__gte=start, created_at__lte=end,
    )
    thread_qs = _apply_filters(thread_qs, "thread", **filters)

    # Get first acknowledged activity per thread
    from django.db.models import Min, Subquery, OuterRef, ExpressionWrapper, DurationField
    ack_logs = ActivityLog.objects.filter(
        thread=OuterRef("pk"),
        action=ActivityLog.Action.ACKNOWLEDGED,
    ).order_by("created_at").values("created_at")[:1]

    threads_with_ack = thread_qs.annotate(
        first_ack=Subquery(ack_logs)
    ).filter(first_ack__isnull=False).annotate(
        response_duration=ExpressionWrapper(
            F("first_ack") - F("created_at"), output_field=DurationField()
        )
    )

    avg_duration = threads_with_ack.aggregate(avg=Avg("response_duration"))["avg"]
    avg_response_minutes = None
    if avg_duration is not None:
        avg_response_minutes = round(avg_duration.total_seconds() / 60, 1)

    # SLA compliance: threads with sla_ack_deadline that were acknowledged in time
    sla_threads = Thread.objects.filter(
        sla_ack_deadline__isnull=False,
        created_at__gte=start,
        created_at__lte=end,
    )
    sla_threads = _apply_filters(sla_threads, "thread", **filters)
    total_sla = sla_threads.count()

    if total_sla == 0:
        sla_compliance_pct = 100.0
    else:
        # Threads acknowledged before deadline
        now = timezone.now()
        first_ack_sub = ActivityLog.objects.filter(
            thread=OuterRef("pk"),
            action=ActivityLog.Action.ACKNOWLEDGED,
        ).order_by("created_at").values("created_at")[:1]

        sla_annotated = sla_threads.annotate(first_ack=Subquery(first_ack_sub))

        # Met = acknowledged before deadline OR still within deadline (not yet due)
        met = sla_annotated.filter(
            Q(first_ack__lte=F("sla_ack_deadline")) |
            Q(first_ack__isnull=True, sla_ack_deadline__gt=now)
        ).count()

        sla_compliance_pct = round((met / total_sla) * 100, 1)

    # Open threads (real-time, ignores date range)
    open_qs = Thread.objects.exclude(status="closed")
    open_qs = _apply_filters(open_qs, "thread", **filters)
    open_threads = open_qs.count()

    return {
        "total_emails": total_emails,
        "avg_response_minutes": avg_response_minutes,
        "sla_compliance_pct": sla_compliance_pct,
        "open_threads": open_threads,
    }


def get_volume_data(start, end, **filters):
    """Email volume by day and inbox for bar/line charts.

    Returns dict with labels (date strings) and datasets (per inbox).
    """
    email_qs = Email.objects.filter(
        is_spam=False, received_at__gte=start, received_at__lte=end,
    )
    email_qs = _apply_filters(email_qs, "email", **filters)

    # Group by date and inbox
    daily = (
        email_qs.annotate(date=TruncDate("received_at"))
        .values("date", "to_inbox")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Build full date range
    date_labels = []
    current = start.date() if hasattr(start, "date") else start
    end_date = end.date() if hasattr(end, "date") else end
    while current <= end_date:
        date_labels.append(current.isoformat())
        current += timedelta(days=1)

    # Collect data per inbox
    inbox_data = defaultdict(lambda: defaultdict(int))
    inboxes = set()
    for row in daily:
        d = row["date"].isoformat()
        inbox = row["to_inbox"]
        inbox_data[inbox][d] = row["count"]
        inboxes.add(inbox)

    # Build datasets
    datasets = []
    for inbox in sorted(inboxes):
        color = INBOX_COLORS.get(inbox, DEFAULT_INBOX_COLOR)
        data = [inbox_data[inbox].get(d, 0) for d in date_labels]
        datasets.append({
            "label": inbox,
            "data": data,
            "backgroundColor": color,
        })

    return {"labels": date_labels, "datasets": datasets}


def get_team_data(start, end, **filters):
    """Team performance: handle counts and avg response per user.

    Returns dict with labels (display names) and datasets (handle_count, avg_response).
    """
    activity_qs = ActivityLog.objects.filter(
        created_at__gte=start,
        created_at__lte=end,
        action__in=[ActivityLog.Action.ACKNOWLEDGED, ActivityLog.Action.CLOSED],
        user__isnull=False,
    )
    activity_qs = _apply_filters(activity_qs, "activity", **filters)

    # Handle count per user
    user_counts = (
        activity_qs.values("user__id", "user__first_name", "user__last_name", "user__username")
        .annotate(handle_count=Count("id"))
        .filter(handle_count__gt=0)
        .order_by("-handle_count")
    )

    labels = []
    handle_counts = []
    avg_responses = []

    from django.db.models import Min, Subquery, OuterRef, ExpressionWrapper, DurationField

    for row in user_counts:
        user_id = row["user__id"]
        first = row["user__first_name"] or ""
        last = row["user__last_name"] or ""
        name = f"{first} {last}".strip() or row["user__username"]
        labels.append(name)
        handle_counts.append(row["handle_count"])

        # Avg response for this user's acknowledged threads
        ack_activities = ActivityLog.objects.filter(
            user_id=user_id,
            action=ActivityLog.Action.ACKNOWLEDGED,
            created_at__gte=start,
            created_at__lte=end,
            thread__isnull=False,
        )
        ack_activities = _apply_filters(ack_activities, "activity", **filters)

        # Calculate avg response for this user's ack actions
        total_minutes = 0
        count = 0
        for act in ack_activities.select_related("thread"):
            if act.thread and act.thread.created_at:
                delta = act.created_at - act.thread.created_at
                total_minutes += delta.total_seconds() / 60
                count += 1

        avg_responses.append(round(total_minutes / count, 1) if count > 0 else 0)

    return {
        "labels": labels,
        "datasets": {
            "handle_count": handle_counts,
            "avg_response_minutes": avg_responses,
        },
    }


def get_corrections_digest():
    """Build corrections digest for last 7 days from ActivityLog.

    Returns dict with correction counts by type, total, and top repeating patterns.
    Used by the triage queue page for gatekeeper/admin awareness.
    """
    from collections import Counter

    cutoff = timezone.now() - timedelta(days=7)

    correction_actions = [
        ActivityLog.Action.CATEGORY_CHANGED,
        ActivityLog.Action.PRIORITY_CHANGED,
        ActivityLog.Action.SPAM_MARKED,
    ]

    # Counts by action type
    counts_qs = (
        ActivityLog.objects.filter(
            action__in=correction_actions,
            created_at__gte=cutoff,
        )
        .values("action")
        .annotate(c=Count("pk"))
    )
    counts = {row["action"]: row["c"] for row in counts_qs}

    category_changes = counts.get(ActivityLog.Action.CATEGORY_CHANGED, 0)
    priority_overrides = counts.get(ActivityLog.Action.PRIORITY_CHANGED, 0)
    spam_corrections = counts.get(ActivityLog.Action.SPAM_MARKED, 0)

    # Top patterns from detail text
    recent_details = list(
        ActivityLog.objects.filter(
            action__in=[
                ActivityLog.Action.CATEGORY_CHANGED,
                ActivityLog.Action.PRIORITY_CHANGED,
            ],
            created_at__gte=cutoff,
        )
        .exclude(detail="")
        .exclude(detail__isnull=True)
        .values_list("detail", flat=True)[:100]
    )

    pattern_counts = Counter(recent_details)
    top_patterns = pattern_counts.most_common(5)

    return {
        "category_changes": category_changes,
        "priority_overrides": priority_overrides,
        "spam_corrections": spam_corrections,
        "total": category_changes + priority_overrides + spam_corrections,
        "top_patterns": top_patterns,  # list of (detail_text, count)
    }


def get_sla_data(start, end, **filters):
    """SLA compliance data: donut chart, trend, and breach list.

    Returns dict with compliance_pct, donut_data, trend, breaches.
    """
    from django.db.models import Min, Subquery, OuterRef

    now = timezone.now()

    sla_threads = Thread.objects.filter(
        sla_ack_deadline__isnull=False,
        created_at__gte=start,
        created_at__lte=end,
    )
    sla_threads = _apply_filters(sla_threads, "thread", **filters)

    first_ack_sub = ActivityLog.objects.filter(
        thread=OuterRef("pk"),
        action=ActivityLog.Action.ACKNOWLEDGED,
    ).order_by("created_at").values("created_at")[:1]

    sla_annotated = sla_threads.annotate(first_ack=Subquery(first_ack_sub))

    total_sla = sla_annotated.count()

    # Met and breached counts
    met = sla_annotated.filter(
        Q(first_ack__lte=F("sla_ack_deadline")) |
        Q(first_ack__isnull=True, sla_ack_deadline__gt=now)
    ).count()

    breached_count = total_sla - met

    compliance_pct = 100.0 if total_sla == 0 else round((met / total_sla) * 100, 1)

    # Daily compliance trend
    trend = []
    current = start.date() if hasattr(start, "date") else start
    end_date = end.date() if hasattr(end, "date") else end
    while current <= end_date:
        day_start = timezone.make_aware(
            timezone.datetime(current.year, current.month, current.day)
        ) if timezone.is_naive(
            timezone.datetime(current.year, current.month, current.day)
        ) else timezone.datetime(current.year, current.month, current.day)

        day_end = day_start + timedelta(days=1)

        day_threads = sla_annotated.filter(created_at__gte=day_start, created_at__lt=day_end)
        day_total = day_threads.count()

        if day_total == 0:
            trend.append({"date": current.isoformat(), "compliance_pct": 100.0})
        else:
            day_met = day_threads.filter(
                Q(first_ack__lte=F("sla_ack_deadline")) |
                Q(first_ack__isnull=True, sla_ack_deadline__gt=now)
            ).count()
            trend.append({
                "date": current.isoformat(),
                "compliance_pct": round((day_met / day_total) * 100, 1),
            })

        current += timedelta(days=1)

    # Recent SLA breaches (last 20)
    breached_threads = sla_annotated.filter(
        Q(first_ack__gt=F("sla_ack_deadline")) |
        Q(first_ack__isnull=True, sla_ack_deadline__lte=now)
    ).order_by("-sla_ack_deadline")[:20]

    breaches = []
    for t in breached_threads:
        exceeded_by = None
        actual = t.first_ack
        if actual and t.sla_ack_deadline:
            exceeded_by = str(actual - t.sla_ack_deadline)
        elif t.sla_ack_deadline:
            exceeded_by = str(now - t.sla_ack_deadline)

        breaches.append({
            "thread_id": t.pk,
            "subject": t.subject,
            "priority": t.priority,
            "deadline": t.sla_ack_deadline.isoformat() if t.sla_ack_deadline else None,
            "actual": actual.isoformat() if actual else "Not acknowledged",
            "exceeded_by": exceeded_by,
        })

    return {
        "compliance_pct": compliance_pct,
        "donut_data": {"met": met, "breached": breached_count},
        "trend": trend,
        "breaches": breaches,
    }
