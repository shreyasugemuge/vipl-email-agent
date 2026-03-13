"""In-memory state manager for circuit breaker and EOD dedup.

Ported from v1's agent/state.py. Pure Python -- no Django imports.
SLA alert tracking removed (deferred to Phase 4).

On restart, worst case is one duplicate EOD (acceptable) and a reset
failure counter (harmless). No persistent state needed.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class StateManager:
    """In-memory state for failure tracking, EOD dedup, and config change detection."""

    def __init__(self):
        self._consecutive_failures: int = 0
        self._config_snapshot: dict[str, str] = {}
        self._last_eod_time: Optional[datetime] = None

    # --- Failure tracking (circuit breaker) ---

    def record_failure(self):
        """Increment consecutive failure counter."""
        self._consecutive_failures += 1

    def reset_failures(self):
        """Reset consecutive failure counter after a successful run."""
        self._consecutive_failures = 0

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    # --- EOD dedup ---

    def can_send_eod(self) -> bool:
        """Return True if an EOD report hasn't been sent in the last 10 minutes."""
        if self._last_eod_time is None:
            return True
        return (datetime.now() - self._last_eod_time).total_seconds() > 600

    def record_eod_sent(self):
        """Record that an EOD report was just sent."""
        self._last_eod_time = datetime.now()

    # --- Config change detection ---

    def detect_config_changes(self, current: dict[str, str]) -> list[dict]:
        """Compare current config against previous snapshot, return list of changes.

        First call establishes baseline and returns no changes.
        """
        changes = []
        previous = self._config_snapshot
        if previous:
            for key, new_val in current.items():
                old_val = previous.get(key, "")
                if str(old_val) != str(new_val):
                    changes.append({
                        "setting": key,
                        "old_value": str(old_val),
                        "new_value": str(new_val),
                    })
        self._config_snapshot = dict(current)
        return changes
