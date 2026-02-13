"""
Chat Notifier — Posts formatted cards to Google Chat via webhook.

Uses Google Chat Cards v2 with proper decoratedText widgets
for clean, structured rendering.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

PRIORITY_CONFIG = {
    "CRITICAL": {"emoji": "\U0001f534", "color": "#D93025"},
    "HIGH":     {"emoji": "\U0001f7e0", "color": "#E37400"},
    "MEDIUM":   {"emoji": "\U0001f7e1", "color": "#F9AB00"},
    "LOW":      {"emoji": "\U0001f7e2", "color": "#0F9D58"},
}


class ChatNotifier:
    """Sends formatted notifications to Google Chat via incoming webhook."""

    def __init__(self, webhook_url: str, sheet_url: str = ""):
        self.webhook_url = webhook_url
        self.sheet_url = sheet_url or "https://docs.google.com/spreadsheets"

    def _post(self, payload: dict) -> bool:
        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            logger.warning(f"Chat webhook returned {response.status_code}: {response.text}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"Chat webhook request failed: {e}")
            return False

    # ----------------------------------------------------------------
    # New Email Notification
    # ----------------------------------------------------------------

    def notify_new_email(self, ticket_number: str, email, triage_result,
                         sla_deadline_str: str) -> bool:
        pri = PRIORITY_CONFIG.get(triage_result.priority, PRIORITY_CONFIG["MEDIUM"])
        assignee = triage_result.suggested_assignee or "Unassigned"

        # Truncate draft reply
        draft_preview = triage_result.draft_reply[:300]
        if len(triage_result.draft_reply) > 300:
            draft_preview += "..."

        card = {
            "header": {
                "title": f"{pri['emoji']} {ticket_number} — {triage_result.priority}",
                "subtitle": email.subject[:80],
                "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/mail/default/48px.svg",
                "imageType": "CIRCLE",
            },
            "sections": [
                {
                    "widgets": [
                        {"decoratedText": {
                            "topLabel": "From",
                            "text": f"{email.sender_name} &lt;{email.sender_email}&gt;",
                        }},
                        {"decoratedText": {
                            "topLabel": "Category",
                            "text": triage_result.category,
                        }},
                        {"decoratedText": {
                            "topLabel": "SLA Deadline",
                            "text": sla_deadline_str,
                        }},
                        {"decoratedText": {
                            "topLabel": "Suggested Assignee",
                            "text": assignee,
                        }},
                    ]
                },
                {
                    "header": "AI Summary",
                    "widgets": [
                        {"textParagraph": {"text": triage_result.summary}},
                    ]
                },
                {
                    "header": "Draft Reply",
                    "collapsible": True,
                    "uncollapsibleWidgetsCount": 0,
                    "widgets": [
                        {"textParagraph": {"text": draft_preview}},
                    ]
                },
                {
                    "widgets": [
                        {"buttonList": {"buttons": [
                            {
                                "text": "Open in Gmail",
                                "onClick": {"openLink": {"url": email.gmail_link}},
                                "color": {"red": 0.10, "green": 0.45, "blue": 0.91, "alpha": 1},
                            },
                            {
                                "text": "Open Tracker",
                                "onClick": {"openLink": {"url": self.sheet_url}},
                            },
                        ]}}
                    ]
                }
            ]
        }

        payload = {"cardsV2": [{"cardId": ticket_number, "card": card}]}
        return self._post(payload)

    # ----------------------------------------------------------------
    # SLA Breach Alert
    # ----------------------------------------------------------------

    def notify_sla_breach(self, ticket: dict, hours_overdue: float) -> bool:
        ticket_num = ticket.get("Ticket #", "Unknown")
        subject = ticket.get("Subject", "No subject")[:80]
        assigned_to = ticket.get("Assigned To", "").strip() or "UNASSIGNED"
        sla_deadline = ticket.get("SLA Deadline", "Unknown")

        card = {
            "header": {
                "title": f"\u26a0\ufe0f SLA BREACH — {ticket_num}",
                "subtitle": f"Overdue by {hours_overdue:.1f} hours",
                "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/warning/default/48px.svg",
                "imageType": "CIRCLE",
            },
            "sections": [
                {
                    "widgets": [
                        {"decoratedText": {"topLabel": "Subject", "text": subject}},
                        {"decoratedText": {"topLabel": "Assigned To", "text": assigned_to}},
                        {"decoratedText": {"topLabel": "SLA Deadline", "text": f"Was {sla_deadline}"}},
                        {"decoratedText": {
                            "topLabel": "Overdue By",
                            "text": f"<font color=\"#D93025\"><b>{hours_overdue:.1f} hours</b></font>",
                        }},
                    ]
                },
                {
                    "widgets": [
                        {"buttonList": {"buttons": [
                            {"text": "Open Tracker", "onClick": {"openLink": {"url": self.sheet_url}}},
                        ]}}
                    ]
                }
            ]
        }

        payload = {"cardsV2": [{"cardId": f"sla-{ticket_num}", "card": card}]}
        return self._post(payload)

    # ----------------------------------------------------------------
    # EOD Summary
    # ----------------------------------------------------------------

    def notify_eod_summary(self, stats: dict) -> bool:
        date_str = stats.get("date", "Today")
        breaches = stats.get("sla_breaches", 0)
        breach_color = "#D93025" if breaches > 0 else "#0F9D58"

        card = {
            "header": {
                "title": f"\U0001f4ca Daily Summary — {date_str}",
                "subtitle": f"{stats.get('received_today', 0)} received | {breaches} breaches",
                "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/analytics/default/48px.svg",
                "imageType": "CIRCLE",
            },
            "sections": [
                {
                    "widgets": [
                        {"decoratedText": {"topLabel": "Received Today", "text": str(stats.get("received_today", 0))}},
                        {"decoratedText": {"topLabel": "Closed Today", "text": str(stats.get("closed_today", 0))}},
                        {"decoratedText": {"topLabel": "Total Open", "text": str(stats.get("total_open", 0))}},
                        {"decoratedText": {
                            "topLabel": "SLA Breaches",
                            "text": f"<font color=\"{breach_color}\"><b>{breaches}</b></font>",
                        }},
                        {"decoratedText": {"topLabel": "Unassigned", "text": str(stats.get("unassigned", 0))}},
                    ]
                },
                {
                    "widgets": [
                        {"buttonList": {"buttons": [
                            {"text": "Open Tracker", "onClick": {"openLink": {"url": self.sheet_url}}},
                        ]}}
                    ]
                }
            ]
        }

        payload = {"cardsV2": [{"cardId": f"eod-{date_str}", "card": card}]}
        return self._post(payload)
