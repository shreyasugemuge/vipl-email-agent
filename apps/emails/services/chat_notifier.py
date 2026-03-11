"""Chat Notifier -- Posts formatted cards to Google Chat via webhook.

Ported from v1's agent/chat_notifier.py. Uses Google Chat Cards v2 format.
Quiet hours checked via SystemConfig. Never crashes the pipeline on failure.
"""

import logging
from datetime import datetime

import httpx
import pytz

from apps.core.models import SystemConfig

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

PRIORITY_EMOJI = {
    "CRITICAL": "\U0001f534",  # Red circle
    "HIGH": "\U0001f7e0",      # Orange circle
    "MEDIUM": "\U0001f7e1",    # Yellow circle
    "LOW": "\U0001f7e2",       # Green circle
}

PRIORITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


class ChatNotifier:
    """Sends formatted notifications to Google Chat via incoming webhook.

    This is the v2 port of agent/chat_notifier.py. Key differences:
    - Takes Django Email model instances (not dicts)
    - Quiet hours read from SystemConfig (not config dict)
    - Tracker URL points to v2 dashboard
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip() if webhook_url else ""

        if not self.webhook_url:
            logger.warning("Chat webhook URL is empty -- notifications will be skipped")
        elif not self.webhook_url.startswith("https://chat.googleapis.com/"):
            logger.warning(f"Chat webhook URL looks invalid: {self.webhook_url[:60]}...")

    def _post(self, payload: dict) -> bool:
        """Post a payload to the Google Chat webhook. Never raises."""
        if not self.webhook_url:
            logger.warning("Chat notification skipped -- no webhook URL configured")
            return False

        try:
            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Chat notification sent successfully")
                return True
            else:
                logger.warning(
                    f"Chat webhook returned {response.status_code}: "
                    f"{response.text[:200]}"
                )
                return False
        except Exception as e:
            logger.error(f"Chat webhook request failed: {type(e).__name__}: {e}")
            return False

    def _is_quiet_hours(self) -> bool:
        """Check if current IST time falls within quiet hours.

        Reads quiet_hours_start and quiet_hours_end from SystemConfig.
        Default: no quiet hours (returns False).
        """
        start_str = SystemConfig.get("quiet_hours_start")
        end_str = SystemConfig.get("quiet_hours_end")

        if not start_str or not end_str:
            return False

        try:
            now = datetime.now(IST).time()
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()

            if start <= end:
                # Same-day range (e.g. 09:00 to 17:00)
                return start <= now <= end
            else:
                # Overnight range (e.g. 20:00 to 08:00)
                return now >= start or now <= end
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid quiet hours config: {e}")
            return False

    def notify_assignment(self, email, assignee) -> bool:
        """Post a notification card when an email is assigned to a team member.

        Args:
            email: Django Email model instance.
            assignee: Django User model instance (the person assigned).

        Returns:
            True if posted successfully, False otherwise.
        """
        if self._is_quiet_hours():
            logger.info("Quiet hours -- suppressing assignment notification for email %s", email.pk)
            return False

        pri = getattr(email, "priority", "MEDIUM") or "MEDIUM"
        emoji = PRIORITY_EMOJI.get(pri, PRIORITY_EMOJI["MEDIUM"])
        subject = (getattr(email, "subject", "") or "")[:50]
        category = getattr(email, "category", "") or ""
        from_name = getattr(email, "from_name", "") or ""
        from_address = getattr(email, "from_address", "") or ""
        ai_summary = (getattr(email, "ai_summary", "") or "")[:200]

        assignee_name = assignee.get_full_name() or assignee.username

        tracker_url = SystemConfig.get(
            "tracker_url", "https://triage.vidarbhainfotech.com"
        )
        dashboard_link = f"{tracker_url}/emails/?selected={email.pk}"

        card = {
            "header": {
                "title": f"Assigned to {assignee_name}: {subject}",
                "subtitle": f"{emoji} {pri} | {category}",
            },
            "sections": [
                {
                    "widgets": [
                        {
                            "decoratedText": {
                                "topLabel": "From",
                                "text": f"{from_name} <{from_address}>",
                            }
                        },
                        {
                            "decoratedText": {
                                "topLabel": "Summary",
                                "text": ai_summary or "(no summary)",
                            }
                        },
                    ]
                },
                {
                    "widgets": [
                        {
                            "buttonList": {
                                "buttons": [
                                    {
                                        "text": "Open in Dashboard",
                                        "onClick": {
                                            "openLink": {"url": dashboard_link}
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
            ],
        }

        payload = {"cardsV2": [{"cardId": f"assign-{email.pk}", "card": card}]}
        return self._post(payload)

    def notify_new_emails(self, emails) -> bool:
        """Post a summary card for newly processed emails.

        Args:
            emails: List of Django Email model instances.

        Returns:
            True if posted successfully, False otherwise.
        """
        if not emails:
            return True

        if self._is_quiet_hours():
            logger.info(
                f"Quiet hours -- suppressing Chat notification for {len(emails)} email(s)"
            )
            return False

        # Count by priority
        pri_counts = {}
        for email in emails:
            p = getattr(email, "priority", "MEDIUM") or "MEDIUM"
            pri_counts[p] = pri_counts.get(p, 0) + 1

        pri_summary = " | ".join(
            f"{PRIORITY_EMOJI.get(p, PRIORITY_EMOJI['MEDIUM'])} {p}: {n}"
            for p, n in sorted(
                pri_counts.items(),
                key=lambda x: PRIORITY_ORDER.index(x[0])
                if x[0] in PRIORITY_ORDER
                else 99,
            )
        )

        count = len(emails)

        # Build per-email line items (top 3 by priority)
        sorted_emails = sorted(
            emails,
            key=lambda e: PRIORITY_ORDER.index(getattr(e, "priority", "MEDIUM"))
            if getattr(e, "priority", "MEDIUM") in PRIORITY_ORDER
            else 99,
        )

        email_widgets = []
        for email in sorted_emails[:3]:
            pri = getattr(email, "priority", "MEDIUM") or "MEDIUM"
            emoji = PRIORITY_EMOJI.get(pri, PRIORITY_EMOJI["MEDIUM"])
            subject = (getattr(email, "subject", "") or "")[:60]
            category = getattr(email, "category", "") or ""
            assignee = getattr(email, "ai_suggested_assignee", "") or "Unassigned"

            line = f"{emoji} {subject}"
            email_widgets.append(
                {
                    "decoratedText": {
                        "topLabel": f"{category} -> {assignee}",
                        "text": line,
                    }
                }
            )

        if count > 3:
            email_widgets.append(
                {"textParagraph": {"text": f"<i>...and {count - 3} more</i>"}}
            )

        # Inbox breakdown
        inbox_counts = {}
        for email in emails:
            inbox = getattr(email, "to_inbox", "") or ""
            inbox_counts[inbox] = inbox_counts.get(inbox, 0) + 1

        inbox_summary = ", ".join(
            f"{inbox}: {n}" for inbox, n in sorted(inbox_counts.items())
        )
        if inbox_summary:
            email_widgets.append(
                {
                    "decoratedText": {
                        "topLabel": "Inboxes",
                        "text": inbox_summary,
                    }
                }
            )

        # Tracker URL
        tracker_url = SystemConfig.get(
            "tracker_url", "https://triage.vidarbhainfotech.com"
        )

        card = {
            "header": {
                "title": f"\U0001f4e8 Poll Summary -- {count} new email(s)",
                "subtitle": pri_summary,
            },
            "sections": [
                {"widgets": email_widgets},
                {
                    "widgets": [
                        {
                            "buttonList": {
                                "buttons": [
                                    {
                                        "text": "Open Tracker",
                                        "onClick": {
                                            "openLink": {"url": tracker_url}
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
            ],
        }

        payload = {"cardsV2": [{"cardId": f"poll-{count}", "card": card}]}
        return self._post(payload)
