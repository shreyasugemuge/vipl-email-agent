"""Custom template tags and filters for the email dashboard."""

from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()

# Base color families for tinted badge styling
# Usage: bg-{{ val|priority_base }}-50 text-{{ val|priority_base }}-700
PRIORITY_BASE = {
    "CRITICAL": "red",
    "HIGH": "orange",
    "MEDIUM": "amber",
    "LOW": "emerald",
}

STATUS_BASE = {
    # Email statuses
    "new": "blue",
    "acknowledged": "violet",
    "replied": "emerald",
    "closed": "slate",
    # ActivityLog actions (Phase 3)
    "assigned": "blue",
    "reassigned": "amber",
    "status_changed": "violet",
    # ActivityLog actions (Phase 4)
    "auto_assigned": "cyan",
    "claimed": "teal",
    "sla_breached": "red",
    "priority_bumped": "orange",
}

PRIORITY_BORDER = {
    "CRITICAL": "border-l-red-500",
    "HIGH": "border-l-orange-500",
    "MEDIUM": "border-l-amber-400",
    "LOW": "border-l-emerald-400",
}


@register.filter
def priority_base(value):
    """Return base color family for priority (e.g., 'red', 'orange')."""
    return PRIORITY_BASE.get(value, "slate")


@register.filter
def status_base(value):
    """Return base color family for status (e.g., 'blue', 'violet')."""
    return STATUS_BASE.get(value, "slate")


@register.filter
def priority_border(value):
    """Return Tailwind left-border class for a priority level."""
    return PRIORITY_BORDER.get(value, "border-l-slate-300")


@register.filter
def priority_color(value):
    """Return Tailwind bg color class for solid priority badges."""
    colors = {"CRITICAL": "red-500", "HIGH": "orange-500", "MEDIUM": "amber-500", "LOW": "emerald-500"}
    return colors.get(value, "slate-400")


@register.filter
def status_color(value):
    """Return Tailwind bg color class for solid status badges."""
    colors = {"new": "blue-500", "acknowledged": "violet-500", "replied": "emerald-500", "closed": "slate-400"}
    return colors.get(value, "slate-400")


@register.filter
def time_ago(value):
    """Return a human-readable 'X ago' string from a datetime."""
    if not value:
        return ""
    return f"{timesince(value)} ago"


# ---------------------------------------------------------------------------
# SLA filters
# ---------------------------------------------------------------------------


@register.filter
def sla_color(deadline):
    """Return Tailwind color string based on time remaining to SLA deadline.

    Returns color family names used in class composition:
      - "slate"  -- no deadline set
      - "red animate-pulse" -- breached (flashing)
      - "emerald" -- > 2 hours remaining
      - "amber"   -- 1-2 hours remaining
      - "orange"  -- 30min to 1 hour
      - "red"     -- < 30 minutes
    """
    if deadline is None:
        return "slate"

    now = timezone.now()
    if now >= deadline:
        return "red animate-pulse"

    remaining = (deadline - now).total_seconds()
    hours = remaining / 3600

    if hours > 2:
        return "emerald"
    elif hours > 1:
        return "amber"
    elif remaining > 1800:  # 30 minutes
        return "orange"
    else:
        return "red"


@register.filter
def sla_countdown(deadline):
    """Return human-readable countdown string for an SLA deadline.

    None -> "--"
    Breached -> "-Xh Ym"
    Under 1 hour -> "Ym"
    Otherwise -> "Xh Ym"
    """
    if deadline is None:
        return "--"

    now = timezone.now()
    diff = (deadline - now).total_seconds()

    if diff <= 0:
        # Breached -- show negative time
        abs_seconds = abs(diff)
        hours = int(abs_seconds // 3600)
        minutes = int((abs_seconds % 3600) // 60)
        if hours > 0:
            return f"-{hours}h {minutes}m"
        return f"-{minutes}m"

    hours = int(diff // 3600)
    minutes = int((diff % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@register.filter
def sla_ack_countdown(email):
    """Shorthand: return sla_countdown for the email's ack deadline."""
    return sla_countdown(getattr(email, "sla_ack_deadline", None))


@register.filter
def dict_get(dictionary, key):
    """Look up a key in a dictionary. Returns None if not found or not a dict."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def in_set(value, the_set):
    """Check if a value is in a set/list/tuple."""
    if the_set is None:
        return False
    return value in the_set
