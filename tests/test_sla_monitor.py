"""
Tests for the SLA Monitor module.

Tests breach detection logic, cooldown behavior, and summary alerting.

Usage:
    pytest tests/test_sla_monitor.py -v
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import pytz

from agent.sla_monitor import SLAMonitor
from agent.state import StateManager

IST = pytz.timezone("Asia/Kolkata")


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

@pytest.fixture
def state_manager():
    """Create a fresh in-memory StateManager."""
    return StateManager()


@pytest.fixture
def mock_sheet():
    """Create a mock SheetLogger."""
    return MagicMock()


@pytest.fixture
def mock_chat():
    """Create a mock ChatNotifier."""
    chat = MagicMock()
    chat.notify_sla_summary.return_value = True
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
            "summary_hours": [9, 13, 17],
        },
        "quiet_hours": {"enabled": False},
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

    def test_breached_ticket_detected(self, sla_monitor, mock_sheet):
        """A ticket past its SLA deadline should be detected as breached."""
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

        breached = sla_monitor.get_breached_tickets()

        assert len(breached) == 1
        assert breached[0]["Ticket #"] == "INF-0001"
        assert breached[0]["hours_overdue"] > 0

    def test_non_breached_ticket_not_detected(self, sla_monitor, mock_sheet):
        """A ticket within its SLA deadline should not be detected."""
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

        breached = sla_monitor.get_breached_tickets()

        assert len(breached) == 0

    def test_empty_ticket_list(self, sla_monitor, mock_sheet):
        """No tickets should result in no breaches."""
        mock_sheet.get_open_tickets.return_value = []

        breached = sla_monitor.get_breached_tickets()

        assert len(breached) == 0

    def test_check_writes_breached_status_to_sheet(self, sla_monitor, mock_sheet):
        """check() should call update_sla_status for breached tickets."""
        past_deadline = (datetime.now(IST) - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        mock_sheet.get_open_tickets.return_value = [
            {
                "Ticket #": "INF-0001",
                "Subject": "Overdue ticket",
                "SLA Deadline": past_deadline,
                "Status": "New",
                "Assigned To": "",
            }
        ]
        sla_monitor.check()
        mock_sheet.update_sla_status.assert_called_with("INF-0001", "Breached")

    def test_invalid_deadline_format_skipped(self, sla_monitor, mock_sheet):
        """Tickets with invalid SLA deadline format should be skipped."""
        mock_sheet.get_open_tickets.return_value = [
            {
                "Ticket #": "INF-0004",
                "Subject": "Bad date ticket",
                "SLA Deadline": "not-a-date",
                "Status": "New",
                "Assigned To": "",
            }
        ]

        breached = sla_monitor.get_breached_tickets()

        assert len(breached) == 0


# ----------------------------------------------------------------
# Tests: Summary Timing
# ----------------------------------------------------------------

class TestSummaryTiming:
    """Test summary-based alerting (3x daily)."""

    def test_is_summary_time_at_configured_hour(self, sla_monitor):
        """Should return True at configured summary hours."""
        from unittest.mock import patch
        with patch("agent.sla_monitor.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 9  # 9 AM is in summary_hours
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert sla_monitor._is_summary_time() is True

    def test_not_summary_time_outside_hours(self, sla_monitor):
        """Should return False outside configured summary hours."""
        from unittest.mock import patch
        with patch("agent.sla_monitor.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 15  # Not in [9, 13, 17]
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert sla_monitor._is_summary_time() is False

    def test_no_duplicate_summary_same_hour(self, sla_monitor):
        """Should not send duplicate summary in the same hour."""
        sla_monitor._last_summary_hour = 9
        from unittest.mock import patch
        with patch("agent.sla_monitor.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 9
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert sla_monitor._is_summary_time() is False


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

    def test_fresh_state(self):
        sm = StateManager()
        assert sm.consecutive_failures == 0

    def test_failure_tracking(self):
        sm = StateManager()
        assert sm.consecutive_failures == 0
        sm.record_failure()
        sm.record_failure()
        assert sm.consecutive_failures == 2
        sm.reset_failures()
        assert sm.consecutive_failures == 0

    def test_record_alert(self):
        sm = StateManager()
        sm.record_alert("INF-0001")
        assert sm.get_last_alert_time("INF-0001") is not None

    def test_get_last_alert_time_unknown(self):
        sm = StateManager()
        assert sm.get_last_alert_time("INF-9999") is None

    def test_clear_alert(self):
        sm = StateManager()
        sm.record_alert("INF-0001")
        sm.clear_alert("INF-0001")
        assert sm.get_last_alert_time("INF-0001") is None

    def test_clear_nonexistent_alert_no_error(self):
        sm = StateManager()
        sm.clear_alert("INF-9999")  # Should not raise

    def test_config_change_detection_first_call_no_changes(self):
        sm = StateManager()
        changes = sm.detect_config_changes({"Poll Interval": "300", "Admin Email": "admin@test.com"})
        assert changes == []  # First call establishes baseline

    def test_config_change_detection_detects_diff(self):
        sm = StateManager()
        sm.detect_config_changes({"Poll Interval": "300", "Admin Email": "admin@test.com"})
        changes = sm.detect_config_changes({"Poll Interval": "120", "Admin Email": "admin@test.com"})
        assert len(changes) == 1
        assert changes[0]["setting"] == "Poll Interval"
        assert changes[0]["old_value"] == "300"
        assert changes[0]["new_value"] == "120"

    def test_config_change_detection_no_diff(self):
        sm = StateManager()
        sm.detect_config_changes({"Poll Interval": "300"})
        changes = sm.detect_config_changes({"Poll Interval": "300"})
        assert changes == []
