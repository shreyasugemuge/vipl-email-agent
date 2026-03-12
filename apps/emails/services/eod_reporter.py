"""EOD Reporter -- Generates and sends the daily end-of-day summary report.

Ported from v1's agent/eod_reporter.py to Django ORM. Aggregates email stats
from PostgreSQL, renders HTML email, sends via Gmail API, posts Chat card.
Feature flags and dedup prevent double-sends.
"""

import base64
import logging
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.models import SystemConfig

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EODReporter:
    """Generates EOD summary stats and sends HTML email + Chat card."""

    def __init__(self, chat_notifier, state_manager, service_account_key_path: str,
                 sender_email: str):
        self.chat = chat_notifier
        self.state_manager = state_manager
        self.sa_key_path = service_account_key_path
        self.sender_email = sender_email

    def generate_stats(self) -> dict:
        """Aggregate today's email stats from Django ORM.

        Returns dict with: received_today, closed_today, total_open, unassigned,
        sla_breaches, by_priority, by_category, avg_time_to_acknowledge,
        avg_time_to_respond, worst_overdue, date.
        """
        from apps.emails.models import Email

        now = timezone.now()
        # Start of today in IST
        import zoneinfo
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")
        today_ist = now.astimezone(ist).replace(hour=0, minute=0, second=0, microsecond=0)

        # Base queryset: completed, non-spam
        base_qs = Email.objects.filter(
            processing_status=Email.ProcessingStatus.COMPLETED,
            is_spam=False,
        )

        # Today's emails
        today_qs = base_qs.filter(received_at__gte=today_ist)
        received_today = today_qs.count()
        closed_today = today_qs.filter(status=Email.Status.CLOSED).count()

        # All-time open
        open_qs = base_qs.exclude(status=Email.Status.CLOSED)
        total_open = open_qs.count()
        unassigned = open_qs.filter(assigned_to__isnull=True).count()

        # SLA breaches (respond deadline passed)
        sla_breaches = base_qs.filter(
            sla_respond_deadline__lt=now,
        ).exclude(status=Email.Status.CLOSED).count()

        # Priority breakdown (today, non-spam, completed)
        by_priority = {}
        pri_counts = today_qs.values("priority").annotate(count=Count("id"))
        for entry in pri_counts:
            if entry["priority"]:
                by_priority[entry["priority"]] = entry["count"]

        # Category breakdown (today, non-spam, completed)
        by_category = {}
        cat_counts = today_qs.values("category").annotate(count=Count("id"))
        for entry in cat_counts:
            if entry["category"]:
                by_category[entry["category"]] = entry["count"]

        # Avg time to acknowledge (for emails that have been ack'd or beyond)
        acked_emails = base_qs.filter(
            status__in=[Email.Status.ACKNOWLEDGED, Email.Status.REPLIED, Email.Status.CLOSED],
            assigned_at__isnull=False,
        )
        avg_ack = None
        if acked_emails.exists():
            total_ack_seconds = 0
            ack_count = 0
            for e in acked_emails:
                if e.assigned_at and e.received_at:
                    delta = (e.assigned_at - e.received_at).total_seconds()
                    if delta > 0:
                        total_ack_seconds += delta
                        ack_count += 1
            if ack_count > 0:
                avg_seconds = total_ack_seconds / ack_count
                avg_ack = _format_duration(avg_seconds)

        # Avg time to respond (for closed emails)
        closed_emails = base_qs.filter(status=Email.Status.CLOSED)
        avg_respond = None
        if closed_emails.exists():
            total_resp_seconds = 0
            resp_count = 0
            for e in closed_emails:
                if e.received_at:
                    delta = (e.updated_at - e.received_at).total_seconds()
                    if delta > 0:
                        total_resp_seconds += delta
                        resp_count += 1
            if resp_count > 0:
                avg_seconds = total_resp_seconds / resp_count
                avg_respond = _format_duration(avg_seconds)

        # Worst overdue (top 5 by time past respond deadline)
        worst_overdue = []
        overdue_qs = base_qs.filter(
            sla_respond_deadline__lt=now,
        ).exclude(status=Email.Status.CLOSED).order_by("sla_respond_deadline")[:5]
        for e in overdue_qs:
            overdue_seconds = (now - e.sla_respond_deadline).total_seconds()
            worst_overdue.append({
                "subject": e.subject[:50],
                "priority": e.priority,
                "overdue_str": _format_duration(overdue_seconds),
                "assignee_name": (
                    e.assigned_to.get_full_name() or e.assigned_to.username
                ) if e.assigned_to else "Unassigned",
            })

        tracker_url = SystemConfig.get(
            "tracker_url", "https://triage.vidarbhainfotech.com"
        )

        return {
            "date": now.astimezone(ist).strftime("%d %b %Y"),
            "received_today": received_today,
            "closed_today": closed_today,
            "total_open": total_open,
            "unassigned": unassigned,
            "sla_breaches": sla_breaches,
            "by_priority": by_priority,
            "by_category": by_category,
            "avg_time_to_acknowledge": avg_ack or "N/A",
            "avg_time_to_respond": avg_respond or "N/A",
            "worst_overdue": worst_overdue,
            "tracker_url": tracker_url,
        }

    def render_email(self, stats: dict) -> str:
        """Render the EOD summary as an HTML email using Django template."""
        try:
            return render_to_string("emails/eod_email.html", stats)
        except Exception as e:
            logger.error(f"Failed to render EOD template: {e}")
            return self._fallback_plain_text(stats)

    @staticmethod
    def _fallback_plain_text(stats: dict) -> str:
        """Generate a plain-text fallback if template rendering fails."""
        lines = [
            f"VIPL Email Agent -- Daily Summary ({stats['date']})",
            "=" * 50,
            f"Received today: {stats['received_today']}",
            f"Closed today: {stats['closed_today']}",
            f"Total open: {stats['total_open']}",
            f"SLA breaches: {stats['sla_breaches']}",
            f"Unassigned: {stats['unassigned']}",
            "",
            f"Tracker: {stats.get('tracker_url', 'N/A')}",
        ]
        return "\n".join(lines)

    def send_report(self):
        """Generate stats, render email, send via Gmail, post Chat card.

        Respects feature flags and dedup (10 min in-memory + SystemConfig).
        """
        # Dedup check (in-memory)
        if not self.state_manager.can_send_eod():
            logger.info("EOD report skipped -- already sent within 10 minutes (in-memory)")
            return

        # Dedup check (persistent -- survives restart)
        last_sent_str = SystemConfig.get("last_eod_sent", "")
        if last_sent_str:
            try:
                from datetime import datetime
                import zoneinfo
                last_sent = datetime.fromisoformat(last_sent_str)
                if (timezone.now() - last_sent).total_seconds() < 600:
                    logger.info("EOD report skipped -- already sent within 10 minutes (persistent)")
                    return
            except (ValueError, TypeError):
                pass  # Invalid timestamp -- proceed

        logger.info("Generating EOD report...")

        try:
            stats = self.generate_stats()
        except Exception as e:
            logger.error(f"Failed to generate EOD stats: {e}")
            return

        # Check feature flags
        eod_email_enabled = SystemConfig.get("eod_email_enabled", True)
        chat_enabled = SystemConfig.get("chat_notifications_enabled", False)

        # Cast to bool if string
        if isinstance(eod_email_enabled, str):
            eod_email_enabled = eod_email_enabled.lower() in ("true", "1", "yes")
        if isinstance(chat_enabled, str):
            chat_enabled = chat_enabled.lower() in ("true", "1", "yes")

        # Post to Google Chat
        if chat_enabled:
            try:
                self.chat.notify_eod_summary(stats)
                logger.info("EOD summary posted to Chat")
            except Exception as e:
                logger.error(f"EOD Chat notification failed: {e}")
        else:
            logger.info("EOD Chat summary suppressed -- chat_notifications_enabled=false")

        # Send HTML email
        if eod_email_enabled:
            try:
                recipients_str = SystemConfig.get("eod_recipients", "")
                recipients = [r.strip() for r in recipients_str.split(",") if r.strip()] if recipients_str else []
                if recipients:
                    html_content = self.render_email(stats)
                    self._send_email(
                        subject=f"VIPL Email Agent -- Daily Summary ({stats['date']})",
                        html_body=html_content,
                        recipients=recipients,
                    )
                    logger.info(f"EOD email sent to {len(recipients)} recipients")
                else:
                    logger.warning("EOD email skipped -- no recipients configured")
            except Exception as e:
                logger.error(f"EOD email failed: {e}")
        else:
            logger.info("EOD email disabled via feature flag")

        # Record send time (both in-memory and persistent)
        self.state_manager.record_eod_sent()
        try:
            SystemConfig.objects.update_or_create(
                key="last_eod_sent",
                defaults={
                    "value": timezone.now().isoformat(),
                    "value_type": "str",
                    "description": "Last EOD report sent timestamp",
                    "category": "scheduler",
                },
            )
        except Exception as e:
            logger.warning(f"Failed to persist last_eod_sent: {e}")

    def _send_email(self, subject: str, html_body: str, recipients: list):
        """Send an HTML email via Gmail API using service account impersonation."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self.sa_key_path,
                scopes=SCOPES,
                subject=self.sender_email,
            )
            gmail_service = build("gmail", "v1", credentials=credentials)

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)

            html_part = MIMEText(html_body, "html")
            message.attach(html_part)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            gmail_service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()

            logger.info(f"EOD email sent: {subject}")
        except Exception as e:
            logger.error(f"Failed to send EOD email: {e}")
            raise

    def _get_gmail_service(self):
        """Create a Gmail service (for external use/testing)."""
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            self.sa_key_path,
            scopes=SCOPES,
            subject=self.sender_email,
        )
        return build("gmail", "v1", credentials=credentials)


def _format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins:
        return f"{hours}h {mins}m"
    return f"{hours}h"
