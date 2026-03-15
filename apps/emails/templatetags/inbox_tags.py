"""Template tags for inbox badge display (INBOX-01, INBOX-03)."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Colors that complement VIPL plum palette (#a83362)
# info@ = teal/cyan pill, sales@ = amber/gold pill
INBOX_COLORS = {
    "info@": {"bg": "#e0f2f1", "text": "#00695c", "border": "#80cbc4"},   # Teal
    "sales@": {"bg": "#fff8e1", "text": "#f57f17", "border": "#ffcc02"},  # Amber
}
DEFAULT_COLOR = {"bg": "#f3e5f5", "text": "#6a1b9a", "border": "#ce93d8"}  # Purple (matches plum)


def _inbox_short(inbox: str) -> str:
    """Convert full email to short label: 'info@vidarbhainfotech.com' -> 'info@'."""
    if "@" in inbox:
        return inbox.split("@")[0] + "@"
    return inbox


@register.simple_tag
def inbox_badge(inbox: str) -> str:
    """Render a single colored pill badge for an inbox.

    Usage: {% inbox_badge email.to_inbox %}
    """
    if not inbox:
        return ""

    short = _inbox_short(inbox)
    colors = INBOX_COLORS.get(short, DEFAULT_COLOR)

    html = (
        f'<span class="inbox-badge" style="'
        f'display:inline-block;padding:2px 8px;border-radius:9999px;'
        f'font-size:0.7rem;font-weight:600;line-height:1.4;'
        f'background:{colors["bg"]};color:{colors["text"]};'
        f'border:1px solid {colors["border"]};'
        f'margin-right:4px;white-space:nowrap;"'
        f'>{short}</span>'
    )
    return mark_safe(html)


@register.simple_tag
def thread_inbox_badges(thread) -> str:
    """Render pill badges for all distinct inboxes on a thread.

    For deduplicated threads, shows both [info@] [sales@].
    Usage: {% thread_inbox_badges thread %}
    """
    if not thread:
        return ""

    # Use prefetched emails if available (avoids N+1 query per card)
    if hasattr(thread, '_prefetched_objects_cache') and 'emails' in thread._prefetched_objects_cache:
        inboxes = sorted({e.to_inbox for e in thread._prefetched_objects_cache['emails'] if e.to_inbox})
    else:
        inboxes = (
            thread.emails
            .values_list("to_inbox", flat=True)
            .distinct()
            .order_by("to_inbox")
        )

    badges = []
    for inbox in inboxes:
        if inbox:
            short = _inbox_short(inbox)
            colors = INBOX_COLORS.get(short, DEFAULT_COLOR)
            badge = (
                f'<span class="inbox-badge" style="'
                f'display:inline-block;padding:2px 8px;border-radius:9999px;'
                f'font-size:0.7rem;font-weight:600;line-height:1.4;'
                f'background:{colors["bg"]};color:{colors["text"]};'
                f'border:1px solid {colors["border"]};'
                f'margin-right:4px;white-space:nowrap;"'
                f'>{short}</span>'
            )
            badges.append(badge)

    return mark_safe("".join(badges))
