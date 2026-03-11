"""Custom template tags and filters for the email dashboard."""

from django import template
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
    "new": "blue",
    "acknowledged": "violet",
    "replied": "emerald",
    "closed": "slate",
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
