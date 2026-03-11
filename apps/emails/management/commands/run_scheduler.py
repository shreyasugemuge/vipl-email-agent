"""APScheduler management command -- runs email polling, dead letter retry, and heartbeat.

Usage: python manage.py run_scheduler

Runs as a separate process from Gunicorn (Docker Compose scheduler service).
Uses BlockingScheduler so the process stays alive.

Jobs:
- Heartbeat: every 1 minute -- writes timestamp to SystemConfig
- Poll: every 5 minutes (configurable) -- calls process_poll_cycle
- Retry: every 30 minutes -- calls retry_failed_emails
"""

import logging
import os
import signal

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from apscheduler.schedulers.blocking import BlockingScheduler

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


class Command(BaseCommand):
    help = "Run the APScheduler-based email polling scheduler"

    def handle(self, **options):
        # Initialize services
        key_path = os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "/app/secrets/service-account.json"
        )
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")

        gmail_poller = GmailPoller(service_account_key_path=key_path)
        ai_processor = AIProcessor(anthropic_api_key=api_key)
        chat_notifier = ChatNotifier(webhook_url=webhook_url)
        state_manager = StateManager()

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

        # Graceful shutdown
        def shutdown_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down scheduler...")
            scheduler.shutdown(wait=False)

        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)

        logger.info(
            f"Starting scheduler: poll every {poll_interval}min, "
            f"retry every 30min, heartbeat every 1min"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduler started (poll={poll_interval}min, retry=30min, heartbeat=1min)"
            )
        )

        scheduler.start()
