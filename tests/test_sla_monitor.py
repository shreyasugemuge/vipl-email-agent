"""
Tests for the SLA Monitor module.

Tests breach detection logic, cooldown behavior, and business-hours mode.

Usage:
    pytest tests/test_sla_monitor.py -v
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytz

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.sla_monitor import SLAMonitor
from agent.state import StateManager

IST = pytz.timezone("Asia/Kolkata")


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

@pytest.fixture
def state_manager(tmp_path):
    """Create a fresh StateManager with a temp file."""
    state_file = str(tmp_path / "test_state.json")
    return StateManager(state_file)


@pytest.fixture
def mock_sheet():
    """Create a mock SheetLogger."""
    return MagicMock()


@pytest.fixture
def mock_chat():
    """Create a mock ChatNotifier."""
    chat = MagicMock()
    chat.notify_sla_breach.return_value = True
    return chat


@pytest.fixture
def default_config():
    """Default SLA configuration."""
    return {
        "sla": {
            "business_hours_only": False,
            "business_hours_start": 9,
            "business_hours_end": 18,
            "business_days": [0, 1, 2, 3, 4, 5],
            "breach_alert_cooldown_hours": 4,
        }
    }


@pytest.fixture
def sla_monitor(mock_sheet, mock_chat, state_manager, default_config):
    """Create an SLAMonitor with mocked dependencies."""
    return SLAMonitor(mock_sheet, mock_chat, state_manager, default_config)


# ----------------------------------------------------------------
# Tests: Breach Detection
# ----------------------------------------------------------------

class TestBreachDetection:
    """Test SLA breach detection logic."""

    def test_breached_ticket_triggers_alert(self, sla_monitor, mock_sheet, mock_chat):
        """A ticket past its SLA deadline should trigger an alert."""
        past_deadline = (datetime.now(IST) - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        mock_sheet.get_open_tickets.return_value = [
            {
                "Ticket #": "INF-0001",
                "Subject": "Test ticket",
                "SLA Deadline": past_deadline,
                "Status": "New",
                "Assigned To": "",
            }
        ]

        sla_monitor.check()

        mock_chat.notify_sla_breach.assert_called_once()
        call_args = mock_chat.notify_sla_breach.call_args
        assert call_args[0][0]["Ticket #"] == "INF-0001"
        assert call_args[0][1] > 0  # hours_overdue should be positive

    def test_non_breached_ticket_no_alert(self, sla_monitor, mock_sheet, mock_chat):
        """A ticket within its SLA deadline should not trigger an alert."""
        future_deadline = (datetime.now(IST) + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
        mock_sheet.get_open_tickets.return_value = [
            {
                "Ticket #": "INF-0002",
                "Subject": "Future ticket",
                "SLA Deadline": future_deadline,
                "Status": "New",
                "Assigned To": "Shreyas",
            }
        ]

        sla_monitor.check()

        mock_chat.notify_sla_breach.assert_not_called()

    def test_closed_ticket_ignored(self, sla_monitor, mock_sheet, mock_chat):
        """Closed tickets should not trigger breach alerts even if past deadline."""
        past_deadline = (datetime.now(IST) - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")
        mock_sheet.get_open_tickets.return_value = [
            {
                "Ticket #": "INF-0003",
                "Subject": "Closed ticket",
                "SLA Deadline": past_deadline,
                "Status": "Closed",
                "Assigned To": "Shreyas",
            }
        ]

        sla_monitor.check()

        mock_chat.notify_sla_breach.assert_not_called()

    def test_empty_ticket_list(self, sla_monitor, mock_sheet, mock_chat):
        """No tickets should result in no alerts."""
        mock_sheet.get_open_tickets.return_value = []

        sla_monitor.check()

        mock_chat.notify_sla_breach.assert_not_called()

    def test_invalid_deadline_format_handled(self, sla_monitor, mock_sheet, mock_chat):
        """Tickets with invalid SLA deadline format should be skipped gracefully."""
        mock_sheet.get_open_tickets.return_value = [
            {
                "Ticket #": "INF-0004",
                "Subject": "Bad date ticket",
                "SLA Deadline": "not-a-date",
                "Status": "New",
                "Assigned To": "",
            }
        ]

        # Should not raise an exception
        sla_monitor.check()

        mock_chat.notify_sla_breach.assert_not_called()


# ----------------------------------------------------------------
# Tests: Alert Cooldown
# ----------------------------------------------------------------

class TestAlertCooldown:
    """Test alert cooldown logic to prevent alert spam."""

    def test_first_alert_always_sent(self, sla_monitor, state_manager):
        """First breach alert for a ticket should always be sent."""
        assert sla_monitor._should_alert("INF-0001") is True

    def test_repeated_alert_within_cooldown_blocked(self, sla_monitor, state_manager):
        """Alert within cooldown period should be suppressed."""
        state_manager.record_alert("INF-0001")

        assert sla_monitor._should_alert("INF-0001") is False

    def test_alert_after_cooldown_allowed(self, sla_monitor, state_manager):
        """Alert after cooldown period should be sent."""
        # Manually set the last alert time to 5 hours ago
        five_hours_ago = (datetime.now() - timedelta(hours=5)).isoformat()
        state_manager.state["sla_alerts"]["INF-0001"] = five_hours_ago
        state_manager.save()

        # Cooldown is 4 hours, so 5 hours ago should allow a new alert
        assert sla_monitor._should_alert("INF-0001") is True

    def test_different_tickets_independent_cooldown(self, sla_monitor, state_manager):
        """Cooldown for one ticket should not affect another."""
        state_manager.record_alert("INF-0001")

        assert sla_monitor._should_alert("INF-0001") is False
        assert sla_monitor._should_alert("INF-0002") is True


# ----------------------------------------------------------------
# Tests: Breached Tickets List
# ----------------------------------------------------------------

class TestGetBreachedTickets:
    """Test the get_breached_tickets method for EOD reporting."""

    def test_returns_only_breached(self, sla_monitor, mock_sheet):
        now = datetime.now(IST)
        past = (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        future = (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")

        mock_sheet.get_open_tickets.return_value = [
            {"Ticket #": "INF-0001", "SLA Deadline": past, "Status": "New", "Assigned To": ""},
            {"Ticket #": "INF-0002", "SLA Deadline": future, "Status": "New", "Assigned To": ""},
        ]

        breached = sla_monitor.get_breached_tickets()

        assert len(breached) == 1
        assert breached[0]["Ticket #"] == "INF-0001"
        assert breached[0]["hours_overdue"] > 0

    def test_empty_when_all_within_sla(self, sla_monitor, mock_sheet):
        future = (datetime.now(IST) + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")
        mock_sheet.get_open_tickets.return_value = [
            {"Ticket #": "INF-0001", "SLA Deadline": future, "Status": "New", "Assigned To": ""},
        ]

        breached = sla_monitor.get_breached_tickets()

        assert len(breached) == 0


# ----------------------------------------------------------------
# Tests: State Manager
# ----------------------------------------------------------------

class TestStateManager:
    """Test the StateManager independently."""

    def test_fresh_state(self, tmp_path):
        sm = StateManager(str(tmp_path / "new_state.json"))
        assert sm.consecutive_failures == 0
        assert not sm.is_processed("thread_123")

    def test_mark_and_check_processed(self, state_manager):
        assert not state_manager.is_processed("thread_abc")
        state_manager.mark_processed("thread_abc")
        assert state_manager.is_processed("thread_abc")

    def test_state_persists_to_disk(self, tmp_path):
        path = str(tmp_path / "persist_state.json")
        sm1 = StateManager(path)
        sm1.mark_processed("thread_xyz")

        # Create a new instance from the same file
        sm2 = StateManager(path)
        assert sm2.is_processed("thread_xyz")

    def test_failure_tracking(self, state_manager):
        assert state_manager.consecutive_failures == 0
        state_manager.record_failure()
        state_manager.record_failure()
        assert state_manager.consecutive_failures == 2
        state_manager.reset_failures()
        assert state_manager.consecutive_failures == 0

    def test_thread_id_limit(self, state_manager):
        """State should cap stored thread IDs at 5000."""
        for i in range(5100):
            state_manager.mark_processed(f"thread_{i}")
        assert len(state_manager.state["processed_threads"]) == 5000
