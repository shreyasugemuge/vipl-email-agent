#!/usr/bin/env python3
"""
VIPL Email Agent — Main Entry Point

AI-powered shared inbox monitoring, triage & response system.
Serves an admin UI on PORT (default 8080) for Cloud Run,
runs background scheduler for email polling, SLA checks, and EOD reports.

Configuration priority:
  1. Environment variables (secrets + org-specific values)
  2. config.yaml (non-sensitive defaults)
  3. Admin UI saves runtime overrides to Google Sheet "Agent Config" tab
"""

import argparse
import logging
import os
import signal
import sys
import time
import threading
from datetime import datetime, timedelta

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
        config.setdefault("google_chat", {})["webhook_url"] = webhook

    # Admin email
    admin_email = os.environ.get("ADMIN_EMAIL")
    if admin_email:
        config.setdefault("admin", {})["email"] = admin_email

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
    """Poll Gmail → Claude triage → Sheet log → Chat notification."""
    config = components["config"]
    gmail = components["gmail"]
    ai = components["ai"]
    sheet = components["sheet"]
    chat = components["chat"]
    state = components["state"]

    inboxes = config.get("gmail", {}).get("inboxes", [])
    sla_defaults = config.get("sla", {}).get("defaults", {})

    try:
        sla_config = sheet.get_sla_config() or {}
        new_emails = gmail.poll_all(inboxes, state)

        if not new_emails:
            state.reset_failures()
            return

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
                chat.notify_new_email(ticket_number, email, triage, sla_deadline_str)

                logger.info(f"\u2705 {ticket_number} | {triage.priority} | {triage.category} | {email.subject[:50]}")

            except Exception as e:
                logger.error(f"Failed to process email '{email.subject[:50]}': {e}")

        state.reset_failures()

    except Exception as e:
        logger.error(f"Email processing cycle failed: {e}")
        state.record_failure()


# ----------------------------------------------------------------
# Flask Admin UI + Health Check
# ----------------------------------------------------------------

def create_app(components: dict, scheduler=None):
    """Create Flask app for admin UI and health check."""
    from flask import Flask, render_template, request, jsonify, redirect

    app = Flask(__name__, template_folder="templates")
    app.config["start_time"] = datetime.now(IST)

    @app.route("/health")
    def health():
        return "OK", 200

    @app.route("/")
    def dashboard():
        cfg = components["config"]
        now = datetime.now(IST)

        try:
            open_tickets = components["sheet"].get_open_tickets()
            today_tickets = components["sheet"].get_all_tickets_today()
            breached = components["sla"].get_breached_tickets()
        except Exception:
            open_tickets, today_tickets, breached = [], [], []

        stats = {
            "total_open": len(open_tickets),
            "received_today": len(today_tickets),
            "sla_breaches": len(breached),
            "unassigned": sum(1 for t in open_tickets if not t.get("Assigned To", "").strip()),
        }

        uptime = now - app.config["start_time"]
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m, _ = divmod(rem, 60)

        return render_template("admin.html",
            page="dashboard", stats=stats, config=cfg,
            uptime=f"{h}h {m}m",
            start_time=app.config["start_time"].strftime("%d %b %Y, %I:%M %p IST"),
            now=now.strftime("%d %b %Y, %I:%M %p IST"),
        )

    @app.route("/config", methods=["GET"])
    def config_page():
        return render_template("admin.html", page="config", config=components["config"])

    @app.route("/config", methods=["POST"])
    def save_config():
        cfg = components["config"]
        sheet = components["sheet"]

        poll_interval = request.form.get("poll_interval", "300")
        eod_hour = request.form.get("eod_hour", "19")
        eod_minute = request.form.get("eod_minute", "0")
        sla_cooldown = request.form.get("sla_cooldown", "4")
        inboxes_str = request.form.get("inboxes", "")
        admin_email = request.form.get("admin_email", "")
        eod_recipients = request.form.get("eod_recipients", "")

        try:
            # Save to Agent Config tab
            config_data = [
                ["Setting", "Value"],
                ["poll_interval_seconds", poll_interval],
                ["eod_hour", eod_hour],
                ["eod_minute", eod_minute],
                ["sla_cooldown_hours", sla_cooldown],
                ["inboxes", inboxes_str],
                ["admin_email", admin_email],
                ["eod_recipients", eod_recipients],
                ["last_updated", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")],
            ]

            tab = cfg.get("google_sheets", {}).get("agent_config_tab", "Agent Config")
            sheet.sheets.values().update(
                spreadsheetId=sheet.spreadsheet_id,
                range=f"'{tab}'!A1:B{len(config_data)}",
                valueInputOption="RAW",
                body={"values": config_data},
            ).execute()

            # Apply to running config
            cfg["gmail"]["poll_interval_seconds"] = int(poll_interval)
            cfg["eod"]["send_hour"] = int(eod_hour)
            cfg["eod"]["send_minute"] = int(eod_minute)
            cfg["sla"]["breach_alert_cooldown_hours"] = int(sla_cooldown)
            if inboxes_str:
                cfg["gmail"]["inboxes"] = [e.strip() for e in inboxes_str.split(",") if e.strip()]
            if admin_email:
                cfg["admin"]["email"] = admin_email
            if eod_recipients:
                cfg["eod"]["recipients"] = [e.strip() for e in eod_recipients.split(",") if e.strip()]

            if scheduler:
                try:
                    scheduler.reschedule_job("email_poll",
                        trigger=IntervalTrigger(seconds=int(poll_interval)))
                except Exception:
                    pass

            logger.info("Config saved via admin UI")
            return redirect("/?saved=1")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return render_template("admin.html", page="config", config=cfg, error=str(e))

    @app.route("/api/status")
    def api_status():
        now = datetime.now(IST)
        state = components["state"]
        try:
            open_t = len(components["sheet"].get_open_tickets())
            today_t = len(components["sheet"].get_all_tickets_today())
            breach_t = len(components["sla"].get_breached_tickets())
        except Exception:
            open_t, today_t, breach_t = 0, 0, 0

        return jsonify({
            "status": "running",
            "uptime_seconds": int((now - app.config["start_time"]).total_seconds()),
            "total_open": open_t,
            "received_today": today_t,
            "sla_breaches": breach_t,
            "failures": state.consecutive_failures,
        })

    return app


# ----------------------------------------------------------------
# Scheduler + Flask
# ----------------------------------------------------------------

def run_agent(components: dict):
    """Start scheduler + Flask admin UI."""
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

    # First poll immediately
    process_emails(components)

    scheduler.start()

    # Flask serves admin UI + health check
    app = create_app(components, scheduler)
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Admin UI on port {port}")
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)


# ----------------------------------------------------------------
# CLI
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
        components["sheet"].ensure_headers()
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
    run_agent(components)


if __name__ == "__main__":
    main()
