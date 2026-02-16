"""
Chat Notifier — Posts formatted cards to Google Chat via webhook.

Uses Google Chat Cards v2 with decoratedText widgets.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

PRIORITY_CONFIG = {
    "CRITICAL": {"emoji": "\U0001f534"},
    "HIGH":     {"emoji": "\U0001f7e0"},
    "MEDIUM":   {"emoji": "\U0001f7e1"},
    "LOW":      {"emoji": "\U0001f7e2"},
}


class ChatNotifier:
    """Sends formatted notifications to Google Chat via incoming webhook."""

    def __init__(self, webhook_url: str, sheet_url: str = ""):
        self.webhook_url = webhook_url.strip() if webhook_url else ""
        self.sheet_url = sheet_url or "https://docs.google.com/spreadsheets"

        if not self.webhook_url:
            logger.warning("Chat webhook URL is empty — notifications will be skipped")
        elif not self.webhook_url.startswith("https://chat.googleapis.com/"):
            logger.warning(f"Chat webhook URL looks invalid: {self.webhook_url[:60]}...")

    def _post(self, payload: dict) -> bool:
        """Post a payload to the Google Chat webhook."""
        if not self.webhook_url:
            logger.warning("Chat notification skipped — no webhook URL configured")
            return False

        try:
            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=15,
            )
            if response.status_code == 200:
                logger.info("Chat notification sent successfully")
                return True
            else:
                logger.warning(f"Chat webhook returned {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Chat webhook request failed: {type(e).__name__}: {e}")
            return False

    # ----------------------------------------------------------------
    # Startup Notification (simple text)
    # ----------------------------------------------------------------

    def notify_startup(self, inboxes: list[str], poll_interval: int) -> bool:
        """Send a simple text message on agent startup to verify webhook works."""
        inbox_list = ", ".join(inboxes)
        payload = {
            "text": f"✅ *VIPL Email Agent started*\nMonitoring: {inbox_list}\nPoll interval: {poll_interval}s"
        }
        result = self._post(payload)
        if result:
            logger.info("Startup notification sent to Chat")
        else:
            logger.warning("Startup notification FAILED — check webhook URL")
        return result

    # ----------------------------------------------------------------
    # Poll Summary — one message per poll cycle
    # ----------------------------------------------------------------

    def notify_poll_summary(self, processed_items: list) -> bool:
        """Send ONE card summarising all emails processed in this poll cycle."""
        if not processed_items:
            return True

        count = len(processed_items)
        # Count by priority
        pri_counts = {}
        for item in processed_items:
            p = item.get("priority", "MEDIUM")
            pri_counts[p] = pri_counts.get(p, 0) + 1

        pri_summary = " | ".join(
            f"{PRIORITY_CONFIG.get(p, PRIORITY_CONFIG['MEDIUM'])['emoji']} {p}: {n}"
            for p, n in sorted(pri_counts.items(), key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(x[0]) if x[0] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else 99)
        )

        # Build per-email line items
        email_widgets = []
        for item in processed_items[:10]:  # Cap at 10 to keep card reasonable
            pri = PRIORITY_CONFIG.get(item["priority"], PRIORITY_CONFIG["MEDIUM"])
            line = f"{pri['emoji']} <b>{item['ticket']}</b> — {item['subject'][:60]}"
            email_widgets.append({"decoratedText": {
                "topLabel": f"{item['category']} → {item['assignee']}",
                "text": line,
            }})

        if count > 10:
            email_widgets.append({"textParagraph": {
                "text": f"<i>...and {count - 10} more</i>"
            }})

        card = {
            "header": {
                "title": f"\U0001f4e8 Poll Summary — {count} new email(s)",
                "subtitle": pri_summary,
            },
            "sections": [
                {"widgets": email_widgets},
                {
                    "widgets": [
                        {"buttonList": {"buttons": [
                            {
                                "text": "Open Tracker",
                                "onClick": {"openLink": {"url": self.sheet_url}},
                            },
                        ]}}
                    ]
                }
            ]
        }

        payload = {"cardsV2": [{"cardId": f"poll-{count}", "card": card}]}
        return self._post(payload)

    # ----------------------------------------------------------------
    # SLA Breach Summary — 3x daily instead of per-ticket spam
    # ----------------------------------------------------------------

    def notify_sla_summary(self, breached_tickets: list[dict]) -> bool:
        """Post a single summary card with all breached tickets.
        Called 3x daily (9 AM, 1 PM, 5 PM) instead of per-ticket."""
        if not breached_tickets:
            return True

        count = len(breached_tickets)
        # Sort by overdue hours (worst first)
        sorted_tickets = sorted(breached_tickets, key=lambda t: t.get("hours_overdue", 0), reverse=True)

        # Build per-ticket line items (cap at 10)
        ticket_widgets = []
        for t in sorted_tickets[:10]:
            ticket_id = t.get("Ticket #", "?")
            subject = t.get("Subject", "No subject")[:50]
            assigned = t.get("Assigned To", "").strip() or "UNASSIGNED"
            overdue = t.get("hours_overdue", 0)

            line = f"<font color=\"#D93025\"><b>{ticket_id}</b></font> — {subject}"
            ticket_widgets.append({"decoratedText": {
                "topLabel": f"{assigned} | {overdue:.1f}h overdue",
                "text": line,
            }})

        if count > 10:
            ticket_widgets.append({"textParagraph": {
                "text": f"<i>...and {count - 10} more breached tickets</i>"
            }})

        card = {
            "header": {
                "title": f"\u26a0\ufe0f SLA Breach Summary — {count} ticket(s)",
                "subtitle": "Worst overdue listed first",
            },
            "sections": [
                {"widgets": ticket_widgets},
                {
                    "widgets": [
                        {"buttonList": {"buttons": [
                            {"text": "Open Tracker", "onClick": {"openLink": {"url": self.sheet_url}}},
                        ]}}
                    ]
                }
            ]
        }

        payload = {"cardsV2": [{"cardId": f"sla-summary-{count}", "card": card}]}
        return self._post(payload)

    # Keep legacy method for backward compat (unused by SLAMonitor now)
    def notify_sla_breach(self, ticket: dict, hours_overdue: float) -> bool:
        """Legacy per-ticket SLA breach alert. Replaced by notify_sla_summary."""
        return self.notify_sla_summary([{**ticket, "hours_overdue": hours_overdue}])

    # ----------------------------------------------------------------
    # EOD Summary
    # ----------------------------------------------------------------

    def notify_eod_summary(self, stats: dict) -> bool:
        date_str = stats.get("date", "Today")
        breaches = stats.get("sla_breaches", 0)

        card = {
            "header": {
                "title": f"\U0001f4ca Daily Summary — {date_str}",
                "subtitle": f"{stats.get('received_today', 0)} received | {breaches} breaches",
            },
            "sections": [
                {
                    "widgets": [
                        {"decoratedText": {"topLabel": "Received Today", "text": str(stats.get("received_today", 0))}},
                        {"decoratedText": {"topLabel": "Closed Today", "text": str(stats.get("closed_today", 0))}},
                        {"decoratedText": {"topLabel": "Total Open", "text": str(stats.get("total_open", 0))}},
                        {"decoratedText": {
                            "topLabel": "SLA Breaches",
                            "text": f"<font color=\"#D93025\"><b>{breaches}</b></font>" if breaches > 0 else "0",
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
