"""
State Manager — Tracks processed Gmail thread IDs and SLA alert timestamps.

Persists state to a JSON file so the agent can resume after restarts
without reprocessing old emails or spamming duplicate alerts.
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent state for the email agent."""

    def __init__(self, state_file: str = "state.json"):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> dict:
        """Load state from disk, or return a fresh state dict."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                logger.info(f"Loaded state with {len(data.get('processed_threads', []))} processed threads")
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load state file: {e}. Starting fresh.")
        return {
            "processed_threads": [],
            "sla_alerts": {},        # ticket_id -> last_alert_timestamp
            "last_run": None,
            "consecutive_failures": 0,
        }

    def save(self):
        """Persist current state to disk."""
        try:
            self.state["last_run"] = datetime.now().isoformat()
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save state: {e}")

    # --- Thread tracking ---

    def is_processed(self, thread_id: str) -> bool:
        """Check if a Gmail thread has already been processed."""
        return thread_id in self.state["processed_threads"]

    def mark_processed(self, thread_id: str):
        """Mark a Gmail thread as processed."""
        if thread_id not in self.state["processed_threads"]:
            self.state["processed_threads"].append(thread_id)
            # Keep only last 5000 thread IDs to prevent unbounded growth
            if len(self.state["processed_threads"]) > 5000:
                self.state["processed_threads"] = self.state["processed_threads"][-5000:]
            self.save()

    # --- SLA alert tracking ---

    def get_last_alert_time(self, ticket_id: str) -> Optional[datetime]:
        """Get the last time an SLA breach alert was sent for a ticket."""
        ts = self.state.get("sla_alerts", {}).get(ticket_id)
        if ts:
            return datetime.fromisoformat(ts)
        return None

    def record_alert(self, ticket_id: str):
        """Record that an SLA breach alert was sent for a ticket."""
        if "sla_alerts" not in self.state:
            self.state["sla_alerts"] = {}
        self.state["sla_alerts"][ticket_id] = datetime.now().isoformat()
        self.save()

    def clear_alert(self, ticket_id: str):
        """Clear SLA alert tracking for a resolved ticket."""
        self.state.get("sla_alerts", {}).pop(ticket_id, None)
        self.save()

    # --- Failure tracking ---

    def record_failure(self):
        """Increment consecutive failure counter."""
        self.state["consecutive_failures"] = self.state.get("consecutive_failures", 0) + 1
        self.save()

    def reset_failures(self):
        """Reset consecutive failure counter after a successful run."""
        self.state["consecutive_failures"] = 0
        self.save()

    @property
    def consecutive_failures(self) -> int:
        return self.state.get("consecutive_failures", 0)
