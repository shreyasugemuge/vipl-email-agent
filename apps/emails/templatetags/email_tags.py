"""Custom template tags and filters for the email dashboard."""

from django import template
from django.utils.timesince import timesince

register = template.Library()

PRIORITY_COLORS = {
    "CRITICAL": "red-600",
    "HIGH": "orange-500",
    "MEDIUM": "yellow-500",
    "LOW": "gray-400",
}

STATUS_COLORS = {
    "new": "blue-500",
    "acknowledged": "purple-500",
    "replied": "green-500",
    "closed": "gray-400",
}


@register.filter
def priority_color(value):
    """Return Tailwind color class for a priority level."""
    return PRIORITY_COLORS.get(value, "gray-400")


@register.filter
def status_color(value):
    """Return Tailwind color class for a status."""
    return STATUS_COLORS.get(value, "gray-400")


@register.filter
def time_ago(value):
    """Return a human-readable 'X ago' string from a datetime."""
    if not value:
        return ""
    return f"{timesince(value)} ago"
