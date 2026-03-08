"""
SLA Monitor — Checks open tickets for SLA deadline breaches.

v2: Summary-based alerts instead of per-ticket spam.
Posts a breach summary to Chat 3x daily (9 AM, 1 PM, 5 PM IST)
instead of alerting on every individual breach.
The check() method still runs every 15 min to update Sheet SLA status.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz

from agent.utils import parse_sheet_datetime, IST

logger = logging.getLogger(__name__)

# Default hours for SLA summary alerts (IST)
DEFAULT_SUMMARY_HOURS = [9, 13, 17]  # 9 AM, 1 PM, 5 PM


class SLAMonitor:
    """Monitors SLA compliance with summary-based alerting.

    Instead of per-ticket Chat alerts (spammy), this collects all breaches
    and posts a single summary card 3x daily at configured hours.
    The check() method still runs every 15 min to keep Sheet SLA status current.
    """

    def __init__(self, sheet_logger, chat_notifier, state_manager, config: dict):
        self.sheet = sheet_logger
        self.chat = chat_notifier
        self.state = state_manager
        self.config = config

        sla_config = config.get("sla", {})
        self.business_hours_only = sla_config.get("business_hours_only", False)
        self.biz_start = sla_config.get("business_hours_start", 9)
        self.biz_end = sla_config.get("business_hours_end", 18)
        self.biz_days = sla_config.get("business_days", [0, 1, 2, 3, 4, 5])
        self.summary_hours = sla_config.get("summary_hours", DEFAULT_SUMMARY_HOURS)

        # Track last summary time to avoid duplicate sends within the same hour
        self._last_summary_hour: Optional[int] = None

    def _is_quiet_hours(self) -> bool:
        """Check if current time falls within quiet hours (no Chat alerts)."""
        qh = self.config.get("quiet_hours", {})
        if not qh.get("enabled", False):
            return False

        now = datetime.now(IST)
        current_hour = now.hour
        start = qh.get("start_hour", 20)
        end = qh.get("end_hour", 8)

        if start > end:
            return current_hour >= start or current_hour < end
        else:
            return start <= current_hour < end

    def _is_summary_time(self) -> bool:
        """Check if it's time to send an SLA breach summary.
        Returns True if current hour matches a summary hour AND
        we haven't already sent a summary this hour."""
        now = datetime.now(IST)
        current_hour = now.hour

        if current_hour not in self.summary_hours:
            return False

        if self._last_summary_hour == current_hour:
            return False  # Already sent this hour

        return True

    def check(self):
        """
        Main SLA check loop. Runs every 15 minutes.
        1. Scans all open tickets and identifies breaches
        2. Updates Sheet SLA status for breached tickets
        3. At summary hours (9 AM, 1 PM, 5 PM), posts ONE summary card to Chat
        """
        logger.info("Running SLA check...")
        now = datetime.now(IST)
        quiet = self._is_quiet_hours()

        try:
            open_tickets = self.sheet.get_open_tickets()
            if not open_tickets:
                logger.debug("No open tickets to check")
                return

            breached = []
            for ticket in open_tickets:
                ticket_id = ticket.get("Ticket #", "")
                sla_deadline_str = ticket.get("SLA Deadline", "")
                status = ticket.get("Status", "").strip()

                if not sla_deadline_str or not ticket_id:
                    continue

                if status in ("Closed", "Spam"):
                    self.state.clear_alert(ticket_id)
                    continue

                sla_deadline = parse_sheet_datetime(sla_deadline_str)
                if sla_deadline is None:
                    logger.warning(f"Cannot parse SLA deadline for {ticket_id}: '{sla_deadline_str}'")
                    try:
                        self.sheet.update_sla_status(ticket_id, "ERROR — Invalid deadline")
                    except Exception:
                        pass
                    continue

                if self.business_hours_only:
                    effective_now = self._business_hours_elapsed(now)
                    effective_deadline = self._business_hours_elapsed(sla_deadline)
                    is_breached = effective_now > effective_deadline
                else:
                    is_breached = now > sla_deadline

                if is_breached:
                    hours_overdue = (now - sla_deadline).total_seconds() / 3600
                    ticket["hours_overdue"] = round(hours_overdue, 1)
                    breached.append(ticket)
                    # Write SLA status back to Sheet
                    try:
                        self.sheet.update_sla_status(ticket_id, "Breached")
                    except Exception as e:
                        logger.warning(f"Could not update SLA status for {ticket_id}: {e}")

            logger.info(f"SLA check: {len(breached)} breached out of {len(open_tickets)} open tickets")

            # Post summary card at scheduled times (3x daily)
            if breached and self._is_summary_time() and not quiet:
                self._send_breach_summary(breached)
                self._last_summary_hour = now.hour
            elif breached and quiet:
                logger.info("Quiet hours — SLA breach summary suppressed")

        except Exception as e:
            logger.error(f"SLA check failed: {e}")

    def _send_breach_summary(self, breached: list[dict]):
        """Post a single summary card with all breached tickets."""
        try:
            self.chat.notify_sla_summary(breached)
            logger.info(f"SLA breach summary sent: {len(breached)} breached tickets")
        except Exception as e:
            logger.error(f"SLA breach summary failed: {e}")

    def _business_hours_elapsed(self, dt: datetime) -> float:
        """Simplified business hours calculation (wall-clock for v1)."""
        return dt.timestamp()

    def get_breached_tickets(self) -> list[dict]:
        """Get all currently breached tickets (for EOD reporting)."""
        now = datetime.now(IST)
        breached = []

        try:
            open_tickets = self.sheet.get_open_tickets()
            for ticket in open_tickets:
                sla_deadline_str = ticket.get("SLA Deadline", "")
                if not sla_deadline_str:
                    continue

                sla_deadline = parse_sheet_datetime(sla_deadline_str)
                if sla_deadline is None:
                    continue

                if now > sla_deadline:
                    hours_overdue = (now - sla_deadline).total_seconds() / 3600
                    ticket["hours_overdue"] = round(hours_overdue, 1)
                    breached.append(ticket)
        except Exception as e:
            logger.error(f"Failed to get breached tickets: {e}")

        return breached
