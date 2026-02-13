"""
EOD Reporter — Generates and sends the daily end-of-day summary email.

Aggregates ticket stats from Google Sheets and sends an HTML email
to configured recipients at 7 PM IST daily.
"""

import base64
import logging
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import pytz
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.send",
]


class EODReporter:
    """Generates EOD summary stats and sends the HTML email report."""

    def __init__(self, sheet_logger, sla_monitor, chat_notifier,
                 service_account_key_path: str, config: dict):
        self.sheet = sheet_logger
        self.sla = sla_monitor
        self.chat = chat_notifier
        self.config = config

        eod_config = config.get("eod", {})
        self.recipients = eod_config.get("recipients", [])
        self.sender_email = config.get("admin", {}).get("email", "")
        self.sheet_url = f"https://docs.google.com/spreadsheets/d/{config['google_sheets']['spreadsheet_id']}"

        # Gmail service for sending (impersonating the admin email)
        self.sa_key_path = service_account_key_path

        # Jinja2 template
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html"]),
        )

    @staticmethod
    def _parse_sheet_datetime(dt_str: str) -> Optional[datetime]:
        """Parse a datetime string from the Google Sheet into a tz-aware IST datetime."""
        if not dt_str:
            return None
        clean = dt_str.strip()
        for suffix in (" IST", " ist"):
            if clean.endswith(suffix):
                clean = clean[: -len(suffix)]
        try:
            dt = datetime.strptime(clean.strip(), "%d %b %Y, %I:%M %p")
            return IST.localize(dt)
        except ValueError:
            try:
                dt = datetime.strptime(clean.strip(), "%Y-%m-%d %H:%M:%S")
                return IST.localize(dt)
            except ValueError:
                return None

    def _get_gmail_service(self):
        """Create a Gmail service for sending the EOD email."""
        credentials = service_account.Credentials.from_service_account_file(
            self.sa_key_path,
            scopes=SCOPES,
            subject=self.sender_email,
        )
        return build("gmail", "v1", credentials=credentials)

    def generate_stats(self) -> dict:
        """Aggregate all stats needed for the EOD report."""
        now = datetime.now(IST)
        today_str = now.strftime("%Y-%m-%d")

        # Get ticket data
        all_tickets = self.sheet.get_all_tickets()
        today_tickets = self.sheet.get_all_tickets_today()
        breached_tickets = self.sla.get_breached_tickets()

        # Calculate stats
        total_open = sum(
            1 for t in all_tickets
            if t.get("Status", "").strip() not in ("Closed", "Spam", "")
        )
        closed_today = sum(
            1 for t in today_tickets
            if t.get("Status", "").strip() == "Closed"
        )
        unassigned = [
            t for t in all_tickets
            if t.get("Status", "").strip() not in ("Closed", "Spam", "")
            and not t.get("Assigned To", "").strip()
        ]

        # Status breakdown
        status_counts = {}
        for t in all_tickets:
            status = t.get("Status", "Unknown").strip() or "Unknown"
            if status not in ("Closed", "Spam"):
                status_counts[status] = status_counts.get(status, 0) + 1

        # Inbox breakdown (today)
        inbox_counts = {}
        for t in today_tickets:
            inbox = t.get("Inbox", "Unknown").strip()
            inbox_counts[inbox] = inbox_counts.get(inbox, 0) + 1

        # Calculate hours since received for unassigned tickets
        for ticket in unassigned:
            ts_str = ticket.get("Timestamp", "")
            ts = self._parse_sheet_datetime(ts_str)
            if ts:
                age_hours = (now - ts).total_seconds() / 3600
                ticket["age_hours"] = round(age_hours, 1)
            else:
                ticket["age_hours"] = 0

        stats = {
            "date": now.strftime("%d %b %Y"),
            "received_today": len(today_tickets),
            "closed_today": closed_today,
            "total_open": total_open,
            "sla_breaches": len(breached_tickets),
            "unassigned": len(unassigned),
            "status_breakdown": status_counts,
            "inbox_breakdown": inbox_counts,
            "breached_tickets": breached_tickets,
            "unassigned_tickets": unassigned,
            "sheet_url": self.sheet_url,
        }

        return stats

    def render_email(self, stats: dict) -> str:
        """Render the EOD summary as an HTML email using the Jinja2 template."""
        try:
            template = self.jinja_env.get_template("eod_email.html")
            return template.render(**stats)
        except Exception as e:
            logger.error(f"Failed to render EOD template: {e}")
            # Fallback to plain text
            return self._fallback_plain_text(stats)

    @staticmethod
    def _fallback_plain_text(stats: dict) -> str:
        """Generate a plain-text fallback if template rendering fails."""
        lines = [
            f"VIPL Email Agent — Daily Summary ({stats['date']})",
            f"=" * 50,
            f"Received today: {stats['received_today']}",
            f"Closed today: {stats['closed_today']}",
            f"Total open: {stats['total_open']}",
            f"SLA breaches: {stats['sla_breaches']}",
            f"Unassigned: {stats['unassigned']}",
            f"",
            f"Tracker: {stats.get('sheet_url', 'N/A')}",
        ]
        return "\n".join(lines)

    def send_report(self):
        """Generate stats, render the email, and send it."""
        logger.info("Generating EOD report...")

        try:
            stats = self.generate_stats()

            # Send HTML email
            html_content = self.render_email(stats)
            self._send_email(
                subject=f"VIPL Email Agent — Daily Summary ({stats['date']})",
                html_body=html_content,
                recipients=self.recipients,
            )

            # Also post summary to Google Chat
            self.chat.notify_eod_summary(stats)

            logger.info(f"EOD report sent to {len(self.recipients)} recipients")

        except Exception as e:
            logger.error(f"Failed to send EOD report: {e}")

    def _send_email(self, subject: str, html_body: str, recipients: list[str]):
        """Send an HTML email via Gmail API."""
        try:
            service = self._get_gmail_service()

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)

            html_part = MIMEText(html_body, "html")
            message.attach(html_part)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            body = {"raw": raw}

            service.users().messages().send(
                userId="me",
                body=body,
            ).execute()

            logger.info(f"EOD email sent: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
