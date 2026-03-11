"""SLA calculator and breach detection for VIPL Email Agent v2.

Business hours: 8 AM - 8 PM IST, Monday through Saturday.
Sunday is not a business day.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone as tz

from apps.emails.models import Email, SLAConfig

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# Business hours constants
BIZ_START = 8   # 8 AM IST
BIZ_END = 20    # 8 PM IST
BIZ_HOURS_PER_DAY = BIZ_END - BIZ_START  # 12 hours
BIZ_DAYS = (0, 1, 2, 3, 4, 5)  # Mon-Sat (Sunday=6 is off)

# Default SLA hours by priority (used when no SLAConfig exists)
DEFAULT_ACK_HOURS = {
    "CRITICAL": 0.25,
    "HIGH": 0.5,
    "MEDIUM": 1.0,
    "LOW": 2.0,
}
DEFAULT_RESPOND_HOURS = {
    "CRITICAL": 2.0,
    "HIGH": 4.0,
    "MEDIUM": 8.0,
    "LOW": 24.0,
}


def _is_business_day(dt: datetime) -> bool:
    """Check if the given datetime falls on a business day (Mon-Sat)."""
    return dt.weekday() in BIZ_DAYS


def _is_business_hours(dt: datetime) -> bool:
    """Check if the given datetime is during business hours."""
    return _is_business_day(dt) and BIZ_START <= dt.hour < BIZ_END


def _next_business_open(dt: datetime) -> datetime:
    """Return the next business day at BIZ_START after the given datetime."""
    dt_ist = dt.astimezone(IST)
    next_day = dt_ist.replace(hour=BIZ_START, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while next_day.weekday() not in BIZ_DAYS:
        next_day += timedelta(days=1)
    return next_day


def _snap_to_business_hours(dt: datetime) -> datetime:
    """Snap a datetime to the nearest business hours start if outside hours.

    - During business hours: return as-is
    - Before open on a business day: snap to same-day open
    - After close or on Sunday: snap to next business day open
    """
    dt_ist = dt.astimezone(IST)

    if not _is_business_day(dt_ist):
        # Sunday (or any non-business day) -> next business day
        return _next_business_open(dt_ist)

    if dt_ist.hour < BIZ_START:
        return dt_ist.replace(hour=BIZ_START, minute=0, second=0, microsecond=0)

    if dt_ist.hour >= BIZ_END:
        return _next_business_open(dt_ist)

    return dt_ist


def calculate_sla_deadline(start_time: datetime, hours: float) -> datetime:
    """Calculate SLA deadline by adding business hours to start_time.

    Business hours: 8 AM - 8 PM IST, Mon-Sat. Skips Sunday.

    Uses an optimized day-block approach:
    1. Snap start to business hours
    2. Calculate remaining hours in current day
    3. If enough, add directly
    4. Otherwise, subtract current day's remaining, jump to next biz day, repeat
    """
    if hours <= 0:
        return _snap_to_business_hours(start_time)

    current = _snap_to_business_hours(start_time)
    remaining = hours

    # Safety limit to prevent infinite loops
    for _ in range(365):
        if remaining <= 0:
            break

        # Hours left in current business day
        current_ist = current.astimezone(IST)
        hours_left_today = BIZ_END - current_ist.hour - current_ist.minute / 60.0

        if remaining <= hours_left_today:
            # Fits within today
            delta = timedelta(hours=remaining)
            return current + delta

        # Consume rest of today, move to next business day
        remaining -= hours_left_today
        current = _next_business_open(current)

    # Fallback (should never reach here with reasonable hours)
    return current


def set_sla_deadlines(email: Email) -> None:
    """Set SLA ack and respond deadlines on an email.

    Looks up SLAConfig for email's priority + category. If not found,
    uses defaults based on priority. Skips spam emails.
    """
    if email.is_spam:
        return

    # Look up config
    try:
        config = SLAConfig.objects.get(
            priority=email.priority, category=email.category,
        )
        ack_hours = config.ack_hours
        respond_hours = config.respond_hours
    except SLAConfig.DoesNotExist:
        ack_hours = DEFAULT_ACK_HOURS.get(email.priority, 1.0)
        respond_hours = DEFAULT_RESPOND_HOURS.get(email.priority, 24.0)

    start = email.received_at
    email.sla_ack_deadline = calculate_sla_deadline(start, ack_hours)
    email.sla_respond_deadline = calculate_sla_deadline(start, respond_hours)
    email.save(update_fields=["sla_ack_deadline", "sla_respond_deadline", "updated_at"])

    logger.info(
        "SLA deadlines set for email %s: ack=%s, respond=%s",
        email.pk, email.sla_ack_deadline, email.sla_respond_deadline,
    )


def get_breached_emails(breach_type: str = "respond"):
    """Return emails that have breached their SLA deadline.

    Args:
        breach_type: "respond" or "ack"

    Returns QuerySet of breached emails (not closed, not spam, completed processing).
    """
    now = tz.now()

    if breach_type == "ack":
        deadline_field = "sla_ack_deadline"
    else:
        deadline_field = "sla_respond_deadline"

    filters = {
        f"{deadline_field}__lt": now,
        f"{deadline_field}__isnull": False,
    }

    return Email.objects.filter(
        **filters,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    ).exclude(
        status=Email.Status.CLOSED,
    )
