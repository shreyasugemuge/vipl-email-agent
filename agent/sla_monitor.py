"""
SLA Monitor — Checks open tickets for SLA deadline breaches.

Runs every 15 minutes (configurable). Reads all open tickets from
the Google Sheet, compares SLA deadlines to current time, and sends
alerts for breached tickets via Google Chat and email.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# Timestamp formats used in the Google Sheet (written by sheet_logger)
# e.g. "13 Feb 2026, 02:30 PM"
SHEET_DATETIME_FORMAT = "%d %b %Y, %I:%M %p"


def _parse_sheet_datetime(dt_str: str) -> Optional[datetime]:
    """Parse a datetime string from the Google Sheet into a tz-aware IST datetime."""
    if not dt_str:
        return None
    # Strip trailing timezone labels like " IST"
    clean = dt_str.strip()
    for suffix in (" IST", " ist"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
    try:
        dt = datetime.strptime(clean.strip(), SHEET_DATETIME_FORMAT)
        return IST.localize(dt)
    except ValueError:
        # Fallback: try ISO format in case older rows exist
        try:
            dt = datetime.strptime(clean.strip(), "%Y-%m-%d %H:%M:%S")
            return IST.localize(dt)
        except ValueError:
            return None


class SLAMonitor:
    """Monitors SLA compliance and triggers breach alerts."""

    def __init__(self, sheet_logger, chat_notifier, state_manager, config: dict):
        self.sheet = sheet_logger
        self.chat = chat_notifier
        self.state = state_manager
        self.config = config

        # SLA settings
        sla_config = config.get("sla", {})
        self.business_hours_only = sla_config.get("business_hours_only", False)
        self.biz_start = sla_config.get("business_hours_start", 9)
        self.biz_end = sla_config.get("business_hours_end", 18)
        self.biz_days = sla_config.get("business_days", [0, 1, 2, 3, 4, 5])  # Mon-Sat
        self.cooldown_hours = sla_config.get("breach_alert_cooldown_hours", 4)

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

    def check(self):
        """
        Main SLA check loop. Reads all open tickets and flags breaches.
        Called by the scheduler every 15 minutes.
        Respects quiet hours — breaches are still tracked but Chat alerts are suppressed.
        """
        logger.info("Running SLA check...")
        now = datetime.now(IST)
        quiet = self._is_quiet_hours()

        if quiet:
            logger.info("Quiet hours active — SLA breach Chat alerts suppressed")

        try:
            open_tickets = self.sheet.get_open_tickets()
            if not open_tickets:
                logger.debug("No open tickets to check")
                return

            breach_count = 0
            for ticket in open_tickets:
                ticket_id = ticket.get("Ticket #", "")
                sla_deadline_str = ticket.get("SLA Deadline", "")
                status = ticket.get("Status", "").strip()

                if not sla_deadline_str or not ticket_id:
                    continue

                # Skip already-closed or spam tickets
                if status in ("Closed", "Spam"):
                    self.state.clear_alert(ticket_id)
                    continue

                # Parse SLA deadline
                sla_deadline = _parse_sheet_datetime(sla_deadline_str)
                if sla_deadline is None:
                    logger.warning(f"Cannot parse SLA deadline for {ticket_id}: '{sla_deadline_str}'")
                    continue

                # Check if business hours mode adjusts the effective deadline
                if self.business_hours_only:
                    effective_now = self._business_hours_elapsed(now)
                    effective_deadline = self._business_hours_elapsed(sla_deadline)
                    is_breached = effective_now > effective_deadline
                else:
                    is_breached = now > sla_deadline

                if is_breached:
                    hours_overdue = (now - sla_deadline).total_seconds() / 3600
                    breach_count += 1

                    # Check cooldown to avoid alert spam — and respect quiet hours
                    if self._should_alert(ticket_id) and not quiet:
                        logger.warning(
                            f"SLA BREACH: {ticket_id} overdue by {hours_overdue:.1f}h"
                        )
                        self.chat.notify_sla_breach(ticket, hours_overdue)
                        self.state.record_alert(ticket_id)

            logger.info(f"SLA check complete. {breach_count} breached tickets out of {len(open_tickets)} open."
                        f"{' [quiet hours — alerts suppressed]' if quiet else ''}")

        except Exception as e:
            logger.error(f"SLA check failed: {e}")

    def _should_alert(self, ticket_id: str) -> bool:
        """Check if we should send an alert (respecting cooldown period)."""
        last_alert = self.state.get_last_alert_time(ticket_id)
        if last_alert is None:
            return True  # Never alerted before

        # Check if cooldown period has passed
        cooldown = timedelta(hours=self.cooldown_hours)
        if datetime.now() - last_alert > cooldown:
            return True

        return False

    def _business_hours_elapsed(self, dt: datetime) -> float:
        """
        Calculate effective business hours from epoch to a given datetime.

        This is a simplified approach: in business-hours mode, the SLA clock
        only ticks during configured business hours on business days.
        For a more precise implementation, you'd track exact elapsed
        business hours between two timestamps.
        """
        # Simplified: just check if current time is within business hours
        # A full implementation would calculate cumulative business hours
        # between the ticket timestamp and now. For v1, we simply check
        # if the deadline has passed in wall-clock time and log a note.
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

                sla_deadline = _parse_sheet_datetime(sla_deadline_str)
                if sla_deadline is None:
                    continue

                if now > sla_deadline:
                    hours_overdue = (now - sla_deadline).total_seconds() / 3600
                    ticket["hours_overdue"] = round(hours_overdue, 1)
                    breached.append(ticket)
        except Exception as e:
            logger.error(f"Failed to get breached tickets: {e}")

        return breached
