#!/usr/bin/env python3
"""
VIPL Email Agent — Main Entry Point

AI-powered shared inbox monitoring, triage & response system.
Serves a minimal health endpoint on PORT (default 8080) for Cloud Run,
runs background scheduler for email polling, SLA checks, and EOD reports.

Configuration priority:
  1. Environment variables (secrets + org-specific values)
  2. config.yaml (non-sensitive defaults)
  3. Google Sheet "Agent Config" tab (runtime overrides)
"""

import logging
import os
import signal
import sys
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
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("vipl-agent")

IST = pytz.timezone("Asia/Kolkata")


# ----------------------------------------------------------------
# In-Memory Log Buffer — errors & highlights only
# ----------------------------------------------------------------

class AgentLogBuffer:
    """Keeps the latest agent errors and highlights for the Agent Config sheet."""

    def __init__(self):
        self._logs = []
        self._lock = threading.Lock()

    def add(self, level: str, message: str):
        """Only store ERROR-level or notable highlight entries (✅ ticket logs)."""
        if level not in ("ERROR", "HIGHLIGHT"):
            return  # Ignore INFO/DEBUG — only errors and highlights
        with self._lock:
            self._logs.append({
                "time": datetime.now(IST).strftime("%d %b %Y, %I:%M:%S %p"),
                "level": level,
                "message": message[:120],
            })
            if len(self._logs) > 50:
                self._logs = self._logs[-50:]

    def latest(self, n: int = 5) -> list[dict]:
        with self._lock:
            return list(self._logs[-n:])


log_buffer = AgentLogBuffer()


# ----------------------------------------------------------------
# Configuration — env vars override config.yaml
# ----------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict:
    """Load config from YAML, then overlay environment variables."""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # --- Overlay environment variables ---

    # Inboxes (comma-separated)
    inboxes_env = os.environ.get("MONITORED_INBOXES")
    if inboxes_env:
        config.setdefault("gmail", {})["inboxes"] = [
            e.strip() for e in inboxes_env.split(",") if e.strip()
        ]

    # Google Sheet ID
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if sheet_id:
        config.setdefault("google_sheets", {})["spreadsheet_id"] = sheet_id

    # Chat webhook
    webhook = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")
    if webhook:
        config.setdefault("google_chat", {})["webhook_url"] = webhook.strip()

    # Admin email
    admin_email = os.environ.get("ADMIN_EMAIL")
    if admin_email:
        config.setdefault("admin", {})["email"] = admin_email.strip()

    # EOD recipients (comma-separated)
    eod_recipients = os.environ.get("EOD_RECIPIENTS")
    if eod_recipients:
        config.setdefault("eod", {})["recipients"] = [
            e.strip() for e in eod_recipients.split(",") if e.strip()
        ]

    # Validate required values
    required = {
        "MONITORED_INBOXES": config.get("gmail", {}).get("inboxes"),
        "GOOGLE_SHEET_ID": config.get("google_sheets", {}).get("spreadsheet_id"),
        "GOOGLE_CHAT_WEBHOOK_URL": config.get("google_chat", {}).get("webhook_url"),
        "ADMIN_EMAIL": config.get("admin", {}).get("email"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.error(f"Missing required config (set as env vars): {', '.join(missing)}")
        sys.exit(1)

    # Ensure EOD recipients defaults to admin email
    if not config.get("eod", {}).get("recipients"):
        config.setdefault("eod", {})["recipients"] = [config["admin"]["email"]]

    logger.info(f"Config loaded — {len(config.get('gmail', {}).get('inboxes', []))} inboxes")
    return config


def load_sheet_config_overrides(sheet_logger, config: dict) -> dict:
    """Read runtime config overrides from the Agent Config sheet tab."""
    try:
        tab_name = config.get("google_sheets", {}).get("agent_config_tab", "Agent Config")
        result = sheet_logger.sheets.values().get(
            spreadsheetId=sheet_logger.spreadsheet_id,
            range=f"'{tab_name}'!A:B",
        ).execute()
        rows = result.get("values", [])

        overrides = {}
        for row in rows:
            if len(row) >= 2:
                overrides[row[0].strip()] = row[1].strip()

        # Apply overrides to config
        if overrides.get("Poll Interval (seconds)"):
            try:
                val = int(overrides["Poll Interval (seconds)"])
                if 60 <= val <= 3600:
                    config["gmail"]["poll_interval_seconds"] = val
            except ValueError:
                pass

        if overrides.get("SLA Alert Cooldown (hours)"):
            try:
                val = int(overrides["SLA Alert Cooldown (hours)"])
                if 1 <= val <= 48:
                    config["sla"]["breach_alert_cooldown_hours"] = val
            except ValueError:
                pass

        if overrides.get("EOD Report Hour (IST)"):
            try:
                val = int(overrides["EOD Report Hour (IST)"])
                if 0 <= val <= 23:
                    config["eod"]["send_hour"] = val
            except ValueError:
                pass

        if overrides.get("EOD Report Minute"):
            try:
                val = int(overrides["EOD Report Minute"])
                if 0 <= val <= 59:
                    config["eod"]["send_minute"] = val
            except ValueError:
                pass

        if overrides.get("Admin Email"):
            config["admin"]["email"] = overrides["Admin Email"]

        if overrides.get("EOD Recipients"):
            recipients = [e.strip() for e in overrides["EOD Recipients"].split(",") if e.strip()]
            if recipients:
                config["eod"]["recipients"] = recipients

        logger.info("Applied config overrides from Agent Config sheet")
        return config

    except Exception as e:
        logger.info(f"No sheet config overrides (first run?): {e}")
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

    state = StateManager(config.get("state", {}).get("file_path", "state.json"))

    gmail = GmailPoller(
        service_account_key_path=sa_key_path,
        processed_label=config.get("gmail", {}).get("processed_label", "Agent/Processed"),
    )

    claude_config = config.get("claude", {})
    ai = AIProcessor(
        model=claude_config.get("model", "claude-sonnet-4-5-20250929"),
        max_tokens=claude_config.get("max_tokens", 1024),
        temperature=claude_config.get("temperature", 0.3),
        system_prompt_path="prompts/triage_prompt.txt",
    )

    sheet = SheetLogger(
        service_account_key_path=sa_key_path,
        spreadsheet_id=sheet_id,
        config=config.get("google_sheets", {}),
    )

    chat = ChatNotifier(
        webhook_url=config.get("google_chat", {}).get("webhook_url", ""),
        sheet_url=sheet_url,
    )

    sla = SLAMonitor(
        sheet_logger=sheet,
        chat_notifier=chat,
        state_manager=state,
        config=config,
    )

    eod = EODReporter(
        sheet_logger=sheet,
        sla_monitor=sla,
        chat_notifier=chat,
        service_account_key_path=sa_key_path,
        config=config,
    )

    return {
        "state": state, "gmail": gmail, "ai": ai, "sheet": sheet,
        "chat": chat, "sla": sla, "eod": eod, "config": config,
    }


# ----------------------------------------------------------------
# Core Processing Pipeline
# ----------------------------------------------------------------

def process_emails(components: dict):
    """Poll Gmail → Claude triage → Sheet log → one Chat summary."""
    config = components["config"]
    gmail = components["gmail"]
    ai = components["ai"]
    sheet = components["sheet"]
    chat = components["chat"]
    state = components["state"]

    inboxes = config.get("gmail", {}).get("inboxes", [])
    sla_defaults = config.get("sla", {}).get("defaults", {})
    last_polled = datetime.now(IST).strftime("%d %b %Y, %I:%M:%S %p")
    processed_items = []  # Collect all for batch Chat summary

    try:
        sla_config = sheet.get_sla_config() or {}
        new_emails = gmail.poll_all(inboxes, state)

        if not new_emails:
            logger.info(f"Poll complete — no new emails across {len(inboxes)} inbox(es)")
            state.reset_failures()
        else:
            logger.info(f"Processing {len(new_emails)} new email(s)...")

            for email in new_emails:
                try:
                    if sheet.is_thread_logged(email.thread_id):
                        continue

                    triage = ai.process(email)
                    category = triage.category
                    sla_hours = sla_config.get(category, {}).get("hours") or sla_defaults.get(category, 24)

                    ticket_number = sheet.log_email(email, triage, sla_hours)
                    sla_deadline = email.timestamp + timedelta(hours=sla_hours)
                    sla_deadline_str = sla_deadline.strftime("%d %b %Y, %I:%M %p IST")

                    # Collect for batch Chat notification
                    processed_items.append({
                        "ticket": ticket_number,
                        "priority": triage.priority,
                        "category": triage.category,
                        "subject": email.subject,
                        "sender": f"{email.sender_name} <{email.sender_email}>",
                        "inbox": email.inbox,
                        "summary": triage.summary,
                        "assignee": triage.suggested_assignee or "Unassigned",
                        "sla_deadline": sla_deadline_str,
                        "gmail_link": email.gmail_link,
                    })

                    log_buffer.add("HIGHLIGHT",
                        f"✅ {ticket_number} | {triage.priority} | {triage.category}")
                    logger.info(f"✅ {ticket_number} | {triage.priority} | {triage.category} | {email.subject[:50]}")

                except Exception as e:
                    log_buffer.add("ERROR", f"Failed: {email.subject[:50]} — {str(e)[:60]}")
                    logger.error(f"Failed to process email '{email.subject[:50]}': {e}")

            state.reset_failures()

        # Send ONE summary Chat message for the entire poll (if any emails processed)
        if processed_items:
            try:
                chat.notify_poll_summary(processed_items)
            except Exception as e:
                log_buffer.add("ERROR", f"Chat summary failed: {str(e)[:60]}")
                logger.error(f"Chat poll summary failed: {e}")

        # Write status + error logs to Agent Config sheet
        try:
            sheet.write_agent_status(last_polled, len(processed_items), log_buffer.latest(5))
        except Exception as e:
            logger.warning(f"Could not write agent status to sheet: {e}")

    except Exception as e:
        log_buffer.add("ERROR", f"Poll cycle failed: {str(e)[:80]}")
        logger.error(f"Email processing cycle failed: {e}")
        state.record_failure()
        # Still update status even on failure
        try:
            sheet.write_agent_status(last_polled, 0, log_buffer.latest(5))
        except Exception:
            pass


# ----------------------------------------------------------------
# Minimal Health Check Server (replaces Flask)
# ----------------------------------------------------------------

class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for Cloud Run health checks."""

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress access logs to avoid clutter
        pass


def start_health_server(port: int):
    """Start a minimal HTTP server for Cloud Run health checks."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server on port {port}")
    return server


# ----------------------------------------------------------------
# Scheduler + Health Server
# ----------------------------------------------------------------

def run_agent(components: dict):
    """Start scheduler + health server."""
    config = components["config"]
    scheduler = BackgroundScheduler(timezone=IST)

    poll_interval = config.get("gmail", {}).get("poll_interval_seconds", 300)
    scheduler.add_job(process_emails, trigger=IntervalTrigger(seconds=poll_interval),
                      args=[components], id="email_poll", name="Email Polling",
                      max_instances=1, coalesce=True)

    sla_interval = config.get("sla", {}).get("check_interval_seconds", 900)
    scheduler.add_job(components["sla"].check, trigger=IntervalTrigger(seconds=sla_interval),
                      id="sla_check", name="SLA Monitor", max_instances=1, coalesce=True)

    eod_hour = config.get("eod", {}).get("send_hour", 19)
    eod_minute = config.get("eod", {}).get("send_minute", 0)
    scheduler.add_job(components["eod"].send_report,
                      trigger=CronTrigger(hour=eod_hour, minute=eod_minute, timezone=IST),
                      id="eod_report", name="EOD Report", max_instances=1)

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    inboxes = config.get("gmail", {}).get("inboxes", [])
    logger.info("=" * 60)
    logger.info("VIPL Email Agent — Starting")
    logger.info(f"  Inboxes:     {', '.join(inboxes)}")
    logger.info(f"  Poll every:  {poll_interval}s")
    logger.info(f"  SLA check:   every {sla_interval}s")
    logger.info(f"  EOD report:  {eod_hour}:{eod_minute:02d} IST")
    logger.info("=" * 60)

    log_buffer.add("HIGHLIGHT", f"Agent started — monitoring {len(inboxes)} inbox(es), polling every {poll_interval}s")

    # Send startup notification to Chat
    try:
        components["chat"].notify_startup(inboxes, poll_interval)
    except Exception as e:
        logger.warning(f"Could not send startup notification: {e}")

    # First poll immediately
    process_emails(components)

    scheduler.start()

    # Health server for Cloud Run (replaces Flask)
    port = int(os.environ.get("PORT", 8080))
    server = start_health_server(port)

    # Keep main thread alive
    try:
        signal.pause()
    except AttributeError:
        # Windows fallback
        import time
        while True:
            time.sleep(3600)


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="VIPL Email Agent")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit")
    parser.add_argument("--eod", action="store_true", help="Trigger EOD report and exit")
    parser.add_argument("--sla", action="store_true", help="Run one SLA check and exit")
    parser.add_argument("--init-sheet", action="store_true", help="Initialize Sheet headers")
    args = parser.parse_args()

    config = load_config(args.config)
    components = init_components(config)

    # Load config overrides from Google Sheet
    config = load_sheet_config_overrides(components["sheet"], config)
    components["config"] = config

    if args.init_sheet:
        components["sheet"].ensure_headers()
        components["sheet"].ensure_agent_config_tab(config)
        return
    if args.once:
        process_emails(components)
        return
    if args.eod:
        components["eod"].send_report()
        return
    if args.sla:
        components["sla"].check()
        return

    components["sheet"].ensure_headers()
    components["sheet"].ensure_agent_config_tab(config)
    components["sheet"].format_email_log_columns()
    run_agent(components)


if __name__ == "__main__":
    main()
