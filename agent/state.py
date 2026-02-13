"""
State Manager — In-memory SLA alert cooldowns and failure tracking.

Pure in-memory state — no file I/O. Cloud Run's ephemeral filesystem
makes JSON persistence useless. On restart, worst case is one duplicate
SLA alert (acceptable) and a reset failure counter (harmless).

Dedup is handled entirely by:
  1. Gmail query filter (-label:Agent/Processed + after:epoch)
  2. Google Sheet thread ID cache (sheet_logger.is_thread_logged)
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class StateManager:
    """In-memory state for SLA alert cooldowns and failure tracking."""

    def __init__(self):
        self._sla_alerts: dict[str, datetime] = {}   # ticket_id -> last alert time
        self._consecutive_failures: int = 0

    # --- SLA alert tracking ---

    def get_last_alert_time(self, ticket_id: str) -> Optional[datetime]:
        """Get the last time an SLA breach alert was sent for a ticket."""
        return self._sla_alerts.get(ticket_id)

    def record_alert(self, ticket_id: str):
        """Record that an SLA breach alert was sent for a ticket."""
        self._sla_alerts[ticket_id] = datetime.now()

    def clear_alert(self, ticket_id: str):
        """Clear SLA alert tracking for a resolved ticket."""
        self._sla_alerts.pop(ticket_id, None)

    # --- Failure tracking ---

    def record_failure(self):
        """Increment consecutive failure counter."""
        self._consecutive_failures += 1

    def reset_failures(self):
        """Reset consecutive failure counter after a successful run."""
        self._consecutive_failures = 0

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures
