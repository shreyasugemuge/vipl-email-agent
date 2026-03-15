"""APScheduler management command -- runs email polling, dead letter retry, EOD, Sheets sync, and heartbeat.

Usage: python manage.py run_scheduler

Runs as a separate process from Gunicorn (Docker Compose scheduler service).
Uses BlockingScheduler so the process stays alive.

Jobs:
- Heartbeat: every 1 minute -- writes timestamp to SystemConfig
- Poll: every 5 minutes (configurable) -- calls process_poll_cycle
- Retry: every 30 minutes -- calls retry_failed_emails
- EOD: daily at 7 PM IST -- sends daily summary email + Chat card
- Sheets sync: every 5 minutes -- syncs emails to Google Sheets "v2 Mirror" tab
"""

import logging
import os
import signal

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from apps.core.models import SystemConfig
from apps.emails.services.chat_notifier import ChatNotifier
from apps.emails.services.gmail_poller import GmailPoller
from apps.emails.services.ai_processor import AIProcessor
from apps.emails.services.state import StateManager

logger = logging.getLogger(__name__)


def _heartbeat_job():
    """Write current timestamp to SystemConfig for liveness monitoring."""
    close_old_connections()
    try:
        SystemConfig.objects.update_or_create(
            key="scheduler_heartbeat",
            defaults={
                "value": timezone.now().isoformat(),
                "value_type": SystemConfig.ValueType.STR,
                "description": "Last scheduler heartbeat timestamp",
                "category": "scheduler",
            },
        )
    except Exception as e:
        logger.error(f"Heartbeat write failed: {e}")


def _poll_job(gmail_poller, ai_processor, chat_notifier, state_manager):
    """Run one poll cycle."""
    close_old_connections()
    try:
        from apps.emails.services.pipeline import process_poll_cycle

        process_poll_cycle(gmail_poller, ai_processor, chat_notifier, state_manager)
    except Exception as e:
        logger.error(f"Poll job failed: {e}")


def _retry_job(ai_processor, gmail_poller):
    """Run dead letter retry."""
    close_old_connections()
    try:
        from apps.emails.services.pipeline import retry_failed_emails

        retry_failed_emails(ai_processor, gmail_poller)
    except Exception as e:
        logger.error(f"Retry job failed: {e}")


def _auto_assign_job():
    """Run auto-assign batch job."""
    close_old_connections()
    try:
        from apps.emails.services.assignment import auto_assign_batch

        auto_assign_batch()
    except Exception as e:
        logger.error(f"Auto-assign job failed: {e}")


def _sla_summary_job(chat_notifier):
    """Run SLA breach check, escalation, and Chat summary."""
    close_old_connections()
    try:
        from apps.emails.services.sla import check_and_escalate_breaches

        check_and_escalate_breaches(chat_notifier=chat_notifier)
    except Exception as e:
        logger.error(f"SLA summary job failed: {e}")


def _eod_job(chat_notifier, state_manager, key_path, sender_email):
    """Run daily EOD report -- email + Chat card."""
    close_old_connections()
    try:
        from apps.emails.services.eod_reporter import EODReporter

        reporter = EODReporter(
            chat_notifier=chat_notifier,
            state_manager=state_manager,
            service_account_key_path=key_path,
            sender_email=sender_email,
        )
        reporter.send_report()
    except Exception as e:
        logger.error(f"EOD job failed: {e}")


def _sheets_sync_job(key_path, sheet_id):
    """Sync emails to Google Sheets 'v2 Mirror' tab (fire-and-forget)."""
    close_old_connections()
    try:
        from apps.emails.services.sheets_sync import SheetsSyncService

        sync = SheetsSyncService(
            service_account_key_path=key_path,
            spreadsheet_id=sheet_id,
        )
        sync.sync_changed_emails()
    except Exception as e:
        logger.error(f"Sheets sync job failed: {e}")


class Command(BaseCommand):
    help = "Run the APScheduler-based email polling scheduler"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single poll cycle then exit (no APScheduler loop)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log what would happen without calling external APIs (Gmail, Claude, Chat)",
        )

    def handle(self, **options):
        run_once = options.get("once", False)
        dry_run = options.get("dry_run", False)

        # Initialize services with graceful missing-credentials handling
        key_path = os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "/app/secrets/service-account.json"
        )
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")

        # Warn about missing credentials instead of crashing
        if not api_key:
            logger.warning(
                "ANTHROPIC_API_KEY not set — AI triage will use fallback mode"
            )
        if not os.path.exists(key_path):
            logger.warning(
                f"Service account key not found at {key_path} — Gmail polling will be disabled"
            )

        gmail_poller = GmailPoller(service_account_key_path=key_path)
        ai_processor = AIProcessor(anthropic_api_key=api_key)
        chat_notifier = ChatNotifier(webhook_url=webhook_url)
        state_manager = StateManager()

        # Restore last_poll_epoch from SystemConfig for deploy safety.
        # Without this, a restart would re-fetch the last 5 emails (first-poll
        # behavior) and re-triage them, wasting Claude API calls.
        saved_epoch = SystemConfig.get("last_poll_epoch", None)
        if saved_epoch is not None:
            try:
                gmail_poller._start_epoch = int(saved_epoch)
                gmail_poller._first_poll_done = True
                logger.info(
                    f"Restored last_poll_epoch={saved_epoch} from SystemConfig "
                    f"— skipping first-poll catch-up"
                )
            except (ValueError, TypeError):
                logger.warning("Invalid last_poll_epoch in SystemConfig, ignoring")

        # --once: run a single poll cycle and exit
        if run_once:
            from apps.emails.services.pipeline import process_poll_cycle

            if dry_run:
                self.stdout.write("DRY RUN: running single poll cycle with fake data...")
                self._dry_run_cycle()
            else:
                self.stdout.write("Running single poll cycle...")
                process_poll_cycle(gmail_poller, ai_processor, chat_notifier, state_manager)
            self.stdout.write(self.style.SUCCESS("Single poll cycle complete."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: --dry-run without --once is not supported. "
                    "Use: python manage.py run_scheduler --once --dry-run"
                )
            )
            return

        # Read poll interval from config (default 5 minutes)
        poll_interval = SystemConfig.get("poll_interval_minutes", 5)
        if not isinstance(poll_interval, int) or poll_interval < 1:
            poll_interval = 5

        scheduler = BlockingScheduler(timezone="Asia/Kolkata")

        # Heartbeat: every 1 minute
        scheduler.add_job(
            _heartbeat_job,
            "interval",
            minutes=1,
            id="heartbeat",
            max_instances=1,
            coalesce=True,
        )

        # Poll: every N minutes
        scheduler.add_job(
            _poll_job,
            "interval",
            minutes=poll_interval,
            args=[gmail_poller, ai_processor, chat_notifier, state_manager],
            id="poll",
            max_instances=1,
            coalesce=True,
        )

        # Retry: every 30 minutes
        scheduler.add_job(
            _retry_job,
            "interval",
            minutes=30,
            args=[ai_processor, gmail_poller],
            id="retry",
            max_instances=1,
            coalesce=True,
        )

        # Auto-assign: every 3 minutes
        scheduler.add_job(
            _auto_assign_job,
            "interval",
            minutes=3,
            id="auto_assign",
            max_instances=1,
            coalesce=True,
        )

        # SLA breach summary: 9 AM, 1 PM, 5 PM IST
        scheduler.add_job(
            _sla_summary_job,
            CronTrigger(hour="9,13,17", minute=0, timezone="Asia/Kolkata"),
            args=[chat_notifier],
            id="sla_breach_summary",
            max_instances=1,
            coalesce=True,
        )

        # EOD report: 7 PM IST daily
        sender_email = (
            os.environ.get("ADMIN_EMAIL", "")
            or SystemConfig.get("admin_email", "")
        )
        scheduler.add_job(
            _eod_job,
            CronTrigger(hour=19, minute=0, timezone="Asia/Kolkata"),
            args=[chat_notifier, state_manager, key_path, sender_email],
            id="eod_report",
            max_instances=1,
            coalesce=True,
        )

        # Sheets sync: every 5 minutes (only if GOOGLE_SHEET_ID is configured)
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
        sheets_sync_label = ""
        if sheet_id:
            scheduler.add_job(
                _sheets_sync_job,
                "interval",
                minutes=5,
                args=[key_path, sheet_id],
                id="sheets_sync",
                max_instances=1,
                coalesce=True,
            )
            sheets_sync_label = ", sheets_sync=5min"
        else:
            logger.info("GOOGLE_SHEET_ID not set — Sheets sync disabled")

        # Startup catch-up: fire EOD if missed today
        self._eod_startup_catchup(chat_notifier, state_manager, key_path, sender_email)

        # Graceful shutdown
        def shutdown_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down scheduler...")
            scheduler.shutdown(wait=False)

        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)

        logger.info(
            f"Starting scheduler: poll every {poll_interval}min, "
            f"retry every 30min, auto-assign every 3min, "
            f"SLA summary at 9/13/17 IST, eod=19:00 IST, heartbeat every 1min"
            f"{sheets_sync_label}"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduler started (poll={poll_interval}min, retry=30min, "
                f"auto-assign=3min, SLA=9/13/17 IST, eod=19:00 IST, heartbeat=1min"
                f"{sheets_sync_label})"
            )
        )

        scheduler.start()

    def _eod_startup_catchup(self, chat_notifier, state_manager, key_path, sender_email):
        """Check if today's EOD was missed and fire it if within business hours.

        Catches the case where scheduler restarted after 7 PM and missed today's EOD.
        Dedup in send_report() prevents double-sends even if this races with cron.
        """
        import zoneinfo
        from datetime import datetime

        ist = zoneinfo.ZoneInfo("Asia/Kolkata")
        now_ist = timezone.now().astimezone(ist)

        # Only catch up during business hours (8 AM - 9 PM IST)
        if not (8 <= now_ist.hour < 21):
            return

        # Check if EOD was already sent today
        last_sent_str = SystemConfig.get("last_eod_sent", "")
        if last_sent_str:
            try:
                last_sent = datetime.fromisoformat(last_sent_str)
                last_sent_ist = last_sent.astimezone(ist)
                if last_sent_ist.date() == now_ist.date():
                    logger.info("EOD startup catch-up: already sent today, skipping")
                    return
            except (ValueError, TypeError):
                pass  # Invalid timestamp -- proceed

        logger.info("EOD startup catch-up: today's EOD was missed, firing now")
        _eod_job(chat_notifier, state_manager, key_path, sender_email)

    def _dry_run_cycle(self):
        """Simulate a poll cycle with fake data — no external API calls."""
        from apps.emails.services.fake_data import make_fake_emails, make_fake_triage
        from apps.emails.services.pipeline import save_email_to_db

        fake_emails = make_fake_emails(3)
        for i, email_msg in enumerate(fake_emails):
            triage = make_fake_triage(index=i)
            email_obj = save_email_to_db(email_msg, triage)
            logger.info(
                f"[DRY RUN] Saved: {email_obj.subject[:50]} -> "
                f"{triage.category}/{triage.priority}"
            )
            self.stdout.write(
                f"  [DRY RUN] Would poll Gmail: skipped\n"
                f"  [DRY RUN] Would call Claude AI: skipped\n"
                f"  [DRY RUN] Would notify Chat: skipped\n"
                f"  [DRY RUN] Saved to DB: {email_obj.subject[:50]} "
                f"({triage.category}/{triage.priority})"
            )
