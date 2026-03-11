"""Dev inspector view — read-only dashboard showing pipeline results.

No login required (dev/test use only). Shows recent emails with
simulated Chat card and email output previews.

URL: /emails/inspect/
"""

import json
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from apps.emails.models import Email


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

    return render(request, "emails/inspect.html", {
        "emails": emails,
        "stats": stats,
        "priority_order": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
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
