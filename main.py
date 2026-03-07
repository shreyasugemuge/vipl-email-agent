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

import json
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
# Logging Setup — JSON structured logging for Cloud Logging
# ----------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Structured JSON log format for Cloud Run / Cloud Logging."""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
            "severity": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Add extra fields if present (e.g. inbox, thread_id, cost_usd)
        for key in ("inbox", "thread_id", "cost_usd", "model", "tokens", "ticket"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, default=str)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
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

    # EOD sender email (optional, falls back to ADMIN_EMAIL)
    eod_sender = os.environ.get("EOD_SENDER_EMAIL")
    if eod_sender:
        config.setdefault("eod", {})["sender_email"] = eod_sender.strip()

    # Ensure EOD recipients defaults to admin email
    if not config.get("eod", {}).get("recipients"):
        config.setdefault("eod", {})["recipients"] = [config["admin"]["email"]]

    logger.info(f"Config loaded — {len(config.get('gmail', {}).get('inboxes', []))} inboxes")
    return config


def load_sheet_config_overrides(sheet_logger, config: dict) -> dict:
    """Read runtime config overrides from the Agent Config sheet tab.
    Called at startup AND before every poll cycle for hot-reload."""
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

        if overrides.get("EOD Sender Email"):
            config.setdefault("eod", {})["sender_email"] = overrides["EOD Sender Email"]

        # --- Feature flags ---
        def _bool(val: str) -> bool:
            return val.strip().upper() in ("TRUE", "YES", "1", "ON")

        if overrides.get("Chat Notifications Enabled"):
            config.setdefault("feature_flags", {})["chat_enabled"] = _bool(overrides["Chat Notifications Enabled"])
        if overrides.get("AI Triage Enabled"):
            config.setdefault("feature_flags", {})["ai_enabled"] = _bool(overrides["AI Triage Enabled"])
        if overrides.get("EOD Email Enabled"):
            config.setdefault("feature_flags", {})["eod_email_enabled"] = _bool(overrides["EOD Email Enabled"])

        # --- Quiet hours ---
        if overrides.get("Quiet Hours Enabled"):
            config.setdefault("quiet_hours", {})["enabled"] = _bool(overrides["Quiet Hours Enabled"])
        if overrides.get("Quiet Hours Start (IST)"):
            try:
                val = int(overrides["Quiet Hours Start (IST)"])
                if 0 <= val <= 23:
                    config.setdefault("quiet_hours", {})["start_hour"] = val
            except ValueError:
                pass
        if overrides.get("Quiet Hours End (IST)"):
            try:
                val = int(overrides["Quiet Hours End (IST)"])
                if 0 <= val <= 23:
                    config.setdefault("quiet_hours", {})["end_hour"] = val
            except ValueError:
                pass

        logger.debug("Applied config overrides from Agent Config sheet")
        return config

    except Exception as e:
        logger.info(f"No sheet config overrides (first run?): {e}")
        return config


def is_quiet_hours(config: dict) -> bool:
    """Check if current time falls within quiet hours (no Chat alerts)."""
    qh = config.get("quiet_hours", {})
    if not qh.get("enabled", False):
        return False

    now = datetime.now(IST)
    current_hour = now.hour
    start = qh.get("start_hour", 20)
    end = qh.get("end_hour", 8)

    # Handle overnight ranges (e.g. 20:00 → 08:00)
    if start > end:
        return current_hour >= start or current_hour < end
    else:
        return start <= current_hour < end


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

    state = StateManager()  # Pure in-memory — SLA alert cooldowns + failure tracking only

    gmail = GmailPoller(
        service_account_key_path=sa_key_path,
        processed_label=config.get("gmail", {}).get("processed_label", "Agent/Processed"),
    )

    claude_config = config.get("claude", {})
    ai = AIProcessor(
        model=claude_config.get("model", "claude-haiku-4-5-20251001"),
        max_tokens=claude_config.get("max_tokens", 512),
        temperature=claude_config.get("temperature", 0.3),
        system_prompt_path="prompts/triage_prompt.txt",
        escalation_model=claude_config.get("escalation_model", "claude-sonnet-4-5-20250929"),
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
    """Poll Gmail → Claude triage → Sheet log → one Chat summary.
    Reloads config from Sheet each cycle for hot-reload of settings."""
    # Hot-reload config from Sheet every poll cycle (no redeploy needed)
    config = load_sheet_config_overrides(components["sheet"], components["config"])
    components["config"] = config

    # Config change audit — detect and log changes to Change Log tab
    try:
        from agent.sheet_logger import SheetLogger
        current_snapshot = {}
        for field_name, default_fn, _ in SheetLogger.CONFIG_FIELDS:
            current_snapshot[field_name] = str(default_fn(config))
        changes = components["state"].detect_config_changes(current_snapshot)
        if changes:
            components["sheet"].log_config_changes(changes)
            logger.info(f"Config changes detected: {[c['setting'] for c in changes]}")
    except Exception as e:
        logger.warning(f"Config audit failed: {e}")

    gmail = components["gmail"]
    ai = components["ai"]
    sheet = components["sheet"]
    chat = components["chat"]

    # Feature flags (default: all enabled)
    flags = config.get("feature_flags", {})
    ai_enabled = flags.get("ai_enabled", True)
    chat_enabled = flags.get("chat_enabled", True)
    quiet = is_quiet_hours(config)

    inboxes = config.get("gmail", {}).get("inboxes", [])
    sla_defaults = config.get("sla", {}).get("defaults", {})
    last_polled = datetime.now(IST).strftime("%d %b %Y, %I:%M:%S %p")
    processed_items = []  # Collect all for batch Chat summary

    try:
        sla_config = sheet.get_sla_config() or {}
        new_emails = gmail.poll_all(inboxes)

        if not new_emails:
            logger.info(f"Poll complete — no new emails across {len(inboxes)} inbox(es)")
        else:
            logger.info(f"Processing {len(new_emails)} new email(s)..."
                        f"{' [AI disabled]' if not ai_enabled else ''}"
                        f"{' [quiet hours]' if quiet else ''}")

            for email in new_emails:
                try:
                    if sheet.is_thread_logged(email.thread_id):
                        continue

                    if ai_enabled:
                        triage = ai.process(email, gmail_poller=gmail)
                    else:
                        # Fallback when AI is disabled — log with defaults
                        from agent.ai_processor import TriageResult
                        triage = TriageResult(
                            category="General Inquiry", priority="MEDIUM",
                            summary="[AI triage disabled — manual review required]",
                            draft_reply="", reasoning="AI disabled via feature flag",
                            tags=["ai-disabled"], model_used="disabled",
                        )

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
                    # Log to dead letter tab for manual review
                    try:
                        sheet.log_failed_triage(email, str(e))
                    except Exception:
                        pass

        # Send ONE summary Chat message for the entire poll (if any emails processed)
        # Respect quiet hours + feature flag
        if processed_items and chat_enabled and not quiet:
            try:
                chat.notify_poll_summary(processed_items)
            except Exception as e:
                log_buffer.add("ERROR", f"Chat summary failed: {str(e)[:60]}")
                logger.error(f"Chat poll summary failed: {e}")
        elif processed_items and quiet:
            logger.info(f"Quiet hours — suppressed Chat notification for {len(processed_items)} email(s)")

        # Write status + error logs to Agent Config sheet
        try:
            sheet.write_agent_status(last_polled, len(processed_items), log_buffer.latest(5))
        except Exception as e:
            logger.warning(f"Could not write agent status to sheet: {e}")

    except Exception as e:
        log_buffer.add("ERROR", f"Poll cycle failed: {str(e)[:80]}")
        logger.error(f"Email processing cycle failed: {e}")
        # Still update status even on failure
        try:
            sheet.write_agent_status(last_polled, 0, log_buffer.latest(5))
        except Exception:
            pass


# ----------------------------------------------------------------
# Dead Letter Retry — retry failed triages periodically
# ----------------------------------------------------------------

def retry_failed_triages(components: dict):
    """Retry failed triages from the Dead Letter tab.
    Runs every 30 min. Max 3 retries per entry, then marks 'Exhausted'."""
    sheet = components["sheet"]
    gmail = components["gmail"]
    ai = components["ai"]
    chat = components["chat"]
    config = components["config"]

    flags = config.get("feature_flags", {})
    ai_enabled = flags.get("ai_enabled", True)
    if not ai_enabled:
        return

    try:
        eligible = sheet.get_failed_triages_for_retry()
        if not eligible:
            return

        logger.info(f"Dead letter retry: {len(eligible)} entry/entries eligible")
        sla_config = sheet.get_sla_config() or {}
        sla_defaults = config.get("sla", {}).get("defaults", {})

        for entry in eligible:
            thread_id = entry.get("Thread ID", "").strip()
            inbox = entry.get("Inbox", "").strip()
            row_num = entry["_row_number"]
            retry_count = int(entry.get("Retry Count", "0") or "0") + 1

            if not thread_id or not inbox:
                logger.warning(f"Dead letter row {row_num}: missing Thread ID or Inbox, skipping")
                sheet.update_failed_triage_retry(row_num, retry_count, "Exhausted")
                continue

            try:
                email = gmail.fetch_thread_message(inbox, thread_id)
                if not email:
                    raise ValueError(f"Could not fetch thread {thread_id}")

                triage = ai.process(email)
                category = triage.category
                sla_hours = sla_config.get(category, {}).get("hours") or sla_defaults.get(category, 24)
                ticket_number = sheet.log_email(email, triage, sla_hours)

                sheet.update_failed_triage_retry(row_num, retry_count, "Success")
                logger.info(f"Dead letter retry SUCCESS: {thread_id} → {ticket_number}")
                log_buffer.add("HIGHLIGHT", f"♻️ Retry success: {ticket_number}")

            except Exception as e:
                logger.warning(f"Dead letter retry attempt {retry_count} failed for {thread_id}: {e}")
                if retry_count >= 3:
                    sheet.update_failed_triage_retry(row_num, retry_count, "Exhausted")
                    # Alert on Chat
                    try:
                        chat_enabled = flags.get("chat_enabled", True)
                        quiet = is_quiet_hours(config)
                        if chat_enabled and not quiet:
                            chat.send_simple_message(
                                f"⚠️ Dead letter exhausted (3 retries): {entry.get('Subject', 'unknown')[:60]} — {str(e)[:80]}"
                            )
                    except Exception:
                        pass
                    log_buffer.add("ERROR", f"Dead letter exhausted: {entry.get('Subject', '')[:50]}")
                else:
                    sheet.update_failed_triage_retry(row_num, retry_count, f"Retry {retry_count} failed")

    except Exception as e:
        logger.error(f"Dead letter retry cycle failed: {e}")


# ----------------------------------------------------------------
# Health Check Server — JSON status endpoint
# ----------------------------------------------------------------

_agent_start_time = datetime.now(IST)
_agent_components = {}  # Set by run_agent() for health endpoint access


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler returning JSON health status with operational metrics."""

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            status = self._build_status()
            body = json.dumps(status, default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _build_status(self) -> dict:
        now = datetime.now(IST)
        uptime = now - _agent_start_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

        status = {
            "status": "healthy",
            "uptime": uptime_str,
            "started_at": _agent_start_time.isoformat(),
            "current_time": now.isoformat(),
        }

        # Add AI usage stats if available
        try:
            status["ai_usage"] = AIProcessor.get_usage_stats()
        except Exception:
            pass

        # Add failure count if available
        if "state" in _agent_components:
            status["consecutive_failures"] = _agent_components["state"].consecutive_failures

        return status

    def log_message(self, format, *args):
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

def startup_self_test(components: dict) -> bool:
    """Verify all integrations work before starting the scheduler.
    Fail fast with clear error if any integration is broken."""
    checks = {}

    # 1. Google Sheets API
    try:
        components["sheet"].sheets.get(
            spreadsheetId=components["sheet"].spreadsheet_id,
            fields="spreadsheetId",
        ).execute()
        checks["sheets_api"] = "OK"
    except Exception as e:
        checks["sheets_api"] = f"FAIL: {e}"

    # 2. Gmail API (test first inbox)
    try:
        inboxes = components["config"].get("gmail", {}).get("inboxes", [])
        if inboxes:
            service = components["gmail"]._get_service(inboxes[0])
            service.users().getProfile(userId="me").execute()
            checks["gmail_api"] = "OK"
        else:
            checks["gmail_api"] = "SKIP: no inboxes"
    except Exception as e:
        checks["gmail_api"] = f"FAIL: {e}"

    # 3. Claude API
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        checks["claude_api"] = "OK" if api_key else "FAIL: no ANTHROPIC_API_KEY"
    except Exception as e:
        checks["claude_api"] = f"FAIL: {e}"

    # 4. Chat webhook
    try:
        webhook = components["config"].get("google_chat", {}).get("webhook_url", "")
        checks["chat_webhook"] = "OK" if webhook.startswith("https://chat.googleapis.com/") else f"WARN: {webhook[:40]}"
    except Exception as e:
        checks["chat_webhook"] = f"FAIL: {e}"

    # Report
    all_ok = all(v == "OK" for v in checks.values())
    for name, result in checks.items():
        level = logging.INFO if result == "OK" else logging.WARNING
        logger.log(level, f"Self-test {name}: {result}")

    if not all_ok:
        logger.warning("Startup self-test: some checks failed — agent will start but may have issues")
    else:
        logger.info("Startup self-test: all integrations OK")

    return all_ok


def run_agent(components: dict):
    """Start scheduler + health server."""
    global _agent_components
    _agent_components = components

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

    scheduler.add_job(retry_failed_triages, trigger=IntervalTrigger(minutes=30),
                      args=[components], id="dead_letter_retry", name="Dead Letter Retry",
                      max_instances=1, coalesce=True)

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

    # Startup self-test — verify all integrations before starting
    startup_self_test(components)

    # Send startup notification to Chat
    try:
        components["chat"].notify_startup(inboxes, poll_interval)
    except Exception as e:
        logger.warning(f"Could not send startup notification: {e}")

    # First poll immediately
    process_emails(components)

    # Send a fresh EOD report on every deploy/startup
    try:
        logger.info("Sending startup EOD report...")
        components["eod"].send_report()
    except Exception as e:
        logger.warning(f"Startup EOD report failed: {e}")

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
    parser.add_argument("--retry", action="store_true", help="Run dead letter retry and exit")
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
    if args.retry:
        retry_failed_triages(components)
        return

    components["sheet"].ensure_headers()
    components["sheet"].ensure_agent_config_tab(config)
    components["sheet"].format_email_log_columns()
    run_agent(components)


if __name__ == "__main__":
    main()
