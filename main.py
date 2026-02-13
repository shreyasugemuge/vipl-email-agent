#!/usr/bin/env python3
"""
VIPL Email Agent — Main Entry Point

AI-powered shared inbox monitoring, triage & response system.
Polls Gmail inboxes, processes emails with Claude, logs to Google Sheets,
posts notifications to Google Chat, monitors SLA compliance,
and sends daily EOD summary reports.

Usage:
    python main.py                  # Run the full agent with scheduler
    python main.py --once           # Run one poll cycle and exit
    python main.py --eod            # Trigger EOD report manually
    python main.py --sla            # Run one SLA check and exit
    python main.py --init-sheet     # Initialize Google Sheet headers
"""

import argparse
import logging
import os
import signal
import sys
import time
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytz
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from agent.gmail_poller import GmailPoller
from agent.ai_processor import AIProcessor
from agent.sheet_logger import SheetLogger
from agent.chat_notifier import ChatNotifier
from agent.sla_monitor import SLAMonitor
from agent.eod_reporter import EODReporter
from agent.state import StateManager

# ----------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", mode="a"),
    ],
)
logger = logging.getLogger("vipl-agent")

IST = pytz.timezone("Asia/Kolkata")


# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded config from {config_path}")
    return config


# ----------------------------------------------------------------
# Component Initialization
# ----------------------------------------------------------------

def init_components(config: dict) -> dict:
    """Initialize all agent components and return them as a dict."""
    sa_key_path = config["google"]["service_account_key_path"]

    # Fallback: if the configured path doesn't exist, try local file
    if not os.path.exists(sa_key_path):
        fallback = "service-account.json"
        if os.path.exists(fallback):
            logger.info(f"SA key not found at {sa_key_path}, using fallback: {fallback}")
            sa_key_path = fallback
        else:
            logger.error(f"Service account key not found at {sa_key_path} or {fallback}")
            sys.exit(1)
    sheet_id = config["google_sheets"]["spreadsheet_id"]
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    # State manager
    state = StateManager(config.get("state", {}).get("file_path", "state.json"))

    # Gmail poller
    gmail = GmailPoller(
        service_account_key_path=sa_key_path,
        processed_label=config.get("gmail", {}).get("processed_label", "Agent/Processed"),
    )

    # AI processor
    claude_config = config.get("claude", {})
    ai = AIProcessor(
        model=claude_config.get("model", "claude-sonnet-4-5-20250929"),
        max_tokens=claude_config.get("max_tokens", 1024),
        temperature=claude_config.get("temperature", 0.3),
        system_prompt_path="prompts/triage_prompt.txt",
    )

    # Sheet logger
    sheet = SheetLogger(
        service_account_key_path=sa_key_path,
        spreadsheet_id=sheet_id,
        config=config.get("google_sheets", {}),
    )

    # Chat notifier
    chat = ChatNotifier(
        webhook_url=config.get("google_chat", {}).get("webhook_url", ""),
        sheet_url=sheet_url,
    )

    # SLA monitor
    sla = SLAMonitor(
        sheet_logger=sheet,
        chat_notifier=chat,
        state_manager=state,
        config=config,
    )

    # EOD reporter
    eod = EODReporter(
        sheet_logger=sheet,
        sla_monitor=sla,
        chat_notifier=chat,
        service_account_key_path=sa_key_path,
        config=config,
    )

    return {
        "state": state,
        "gmail": gmail,
        "ai": ai,
        "sheet": sheet,
        "chat": chat,
        "sla": sla,
        "eod": eod,
        "config": config,
    }


# ----------------------------------------------------------------
# Core Processing Pipeline
# ----------------------------------------------------------------

def process_emails(components: dict):
    """
    Main email processing pipeline:
    1. Poll Gmail for new emails
    2. Process each through Claude
    3. Log to Google Sheet
    4. Post notification to Google Chat
    """
    config = components["config"]
    gmail = components["gmail"]
    ai = components["ai"]
    sheet = components["sheet"]
    chat = components["chat"]
    state = components["state"]

    inboxes = config.get("gmail", {}).get("inboxes", [])
    sla_defaults = config.get("sla", {}).get("defaults", {})

    try:
        # Read SLA config from Sheet (falls back to config.yaml defaults)
        sla_config = sheet.get_sla_config() or {}

        # Poll all inboxes
        new_emails = gmail.poll_all(inboxes, state)

        if not new_emails:
            logger.debug("No new emails this cycle")
            state.reset_failures()
            return

        logger.info(f"Processing {len(new_emails)} new email(s)...")

        for email in new_emails:
            try:
                # Double-check deduplication against Sheet
                if sheet.is_thread_logged(email.thread_id):
                    logger.info(f"Thread {email.thread_id} already in Sheet, skipping")
                    continue

                # AI triage
                triage = ai.process(email)

                # Determine SLA hours for this category
                category = triage.category
                if category in sla_config:
                    sla_hours = sla_config[category].get("hours", 24)
                elif category in sla_defaults:
                    sla_hours = sla_defaults[category]
                else:
                    sla_hours = 24  # Fallback

                # Log to Sheet
                ticket_number = sheet.log_email(email, triage, sla_hours)

                # Calculate SLA deadline string for the notification
                sla_deadline = email.timestamp + timedelta(hours=sla_hours)
                sla_deadline_str = sla_deadline.strftime("%d %b %Y, %I:%M %p IST")

                # Post to Google Chat
                chat.notify_new_email(ticket_number, email, triage, sla_deadline_str)

                priority_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
                    triage.priority, "⚪"
                )
                logger.info(
                    f"✅ {ticket_number} | {priority_emoji} {triage.priority} | "
                    f"{triage.category} | {email.subject[:50]}"
                )

            except Exception as e:
                logger.error(f"Failed to process email '{email.subject[:50]}': {e}")
                continue

        state.reset_failures()

    except Exception as e:
        logger.error(f"Email processing cycle failed: {e}")
        state.record_failure()

        # Alert admin after consecutive failures
        max_failures = config.get("admin", {}).get("max_consecutive_failures", 3)
        if state.consecutive_failures >= max_failures:
            admin_email = config.get("admin", {}).get("email", "")
            logger.critical(
                f"⚠️ {state.consecutive_failures} consecutive failures! "
                f"Admin alert should be sent to {admin_email}"
            )
            # Post failure alert to Google Chat
            chat.notify_eod_summary({
                "date": datetime.now(IST).strftime("%d %b %Y"),
                "received_today": 0,
                "closed_today": 0,
                "total_open": "?",
                "sla_breaches": "?",
                "unassigned": "⚠️ AGENT ERROR — Check logs",
            })


# ----------------------------------------------------------------
# Health Check HTTP Server (required by Cloud Run)
# ----------------------------------------------------------------

class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for Cloud Run health checks."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"VIPL Email Agent is running")

    def log_message(self, format, *args):
        pass  # Suppress request logs


def start_health_server():
    """Start a background HTTP server on PORT (default 8080) for Cloud Run."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server listening on port {port}")


# ----------------------------------------------------------------
# Scheduler Setup
# ----------------------------------------------------------------

def run_scheduler(components: dict):
    """Set up and start the APScheduler with all scheduled tasks."""
    config = components["config"]

    # Start health check server for Cloud Run
    start_health_server()

    scheduler = BackgroundScheduler(timezone=IST)

    # Email polling — every 3 minutes (configurable)
    poll_interval = config.get("gmail", {}).get("poll_interval_seconds", 180)
    scheduler.add_job(
        process_emails,
        trigger=IntervalTrigger(seconds=poll_interval),
        args=[components],
        id="email_poll",
        name="Email Polling",
        max_instances=1,
        coalesce=True,
    )

    # SLA check — every 15 minutes (configurable)
    sla_interval = config.get("sla", {}).get("check_interval_seconds", 900)
    scheduler.add_job(
        components["sla"].check,
        trigger=IntervalTrigger(seconds=sla_interval),
        id="sla_check",
        name="SLA Monitor",
        max_instances=1,
        coalesce=True,
    )

    # EOD report — daily at configured time (default 7 PM IST)
    eod_hour = config.get("eod", {}).get("send_hour", 19)
    eod_minute = config.get("eod", {}).get("send_minute", 0)
    scheduler.add_job(
        components["eod"].send_report,
        trigger=CronTrigger(hour=eod_hour, minute=eod_minute, timezone=IST),
        id="eod_report",
        name="EOD Report",
        max_instances=1,
    )

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Received shutdown signal, stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("=" * 60)
    logger.info("VIPL Email Agent — Starting")
    logger.info(f"  Inboxes:     {', '.join(config.get('gmail', {}).get('inboxes', []))}")
    logger.info(f"  Poll every:  {poll_interval}s")
    logger.info(f"  SLA check:   every {sla_interval}s")
    logger.info(f"  EOD report:  {eod_hour}:{eod_minute:02d} IST")
    logger.info(f"  Claude:      {config.get('claude', {}).get('model', 'unknown')}")
    logger.info("=" * 60)

    # Run first poll immediately
    process_emails(components)

    # Start scheduler and keep main thread alive
    scheduler.start()
    while True:
        time.sleep(60)


# ----------------------------------------------------------------
# CLI Entry Points
# ----------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="VIPL Email Agent")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit")
    parser.add_argument("--eod", action="store_true", help="Trigger EOD report and exit")
    parser.add_argument("--sla", action="store_true", help="Run one SLA check and exit")
    parser.add_argument("--init-sheet", action="store_true", help="Initialize Sheet headers")
    args = parser.parse_args()

    config = load_config(args.config)
    components = init_components(config)

    if args.init_sheet:
        logger.info("Initializing Google Sheet headers...")
        components["sheet"].ensure_headers()
        logger.info("Done.")
        return

    if args.once:
        logger.info("Running single poll cycle...")
        process_emails(components)
        logger.info("Done.")
        return

    if args.eod:
        logger.info("Triggering EOD report...")
        components["eod"].send_report()
        logger.info("Done.")
        return

    if args.sla:
        logger.info("Running SLA check...")
        components["sla"].check()
        logger.info("Done.")
        return

    # Always ensure Sheet headers exist before running
    logger.info("Ensuring Sheet headers are initialized...")
    components["sheet"].ensure_headers()

    # Default: run the full scheduler
    run_scheduler(components)


if __name__ == "__main__":
    main()
