"""Tests for agent/eod_reporter.py — all mocked, no real APIs."""

from unittest.mock import MagicMock, patch
from datetime import datetime

import pytz

from agent.eod_reporter import EODReporter


IST = pytz.timezone("Asia/Kolkata")


def _make_reporter(config=None, mock_sheet=None, mock_chat=None):
    """Create an EODReporter with mocked dependencies."""
    if config is None:
        config = {
            "eod": {"recipients": ["admin@test.com"], "send_hour": 19, "send_minute": 0},
            "admin": {"email": "admin@test.com"},
            "google_sheets": {"spreadsheet_id": "test-sheet-id", "agent_config_tab": "Agent Config"},
            "feature_flags": {"eod_email_enabled": True},
        }
    sheet = mock_sheet or MagicMock()
    chat = mock_chat or MagicMock()
    sla = MagicMock()
    sla.get_breached_tickets.return_value = []

    return EODReporter(sheet, sla, chat, "/tmp/fake-sa.json", config), sheet, sla, chat


class TestGenerateStats:
    """Test generate_stats aggregation."""

    def test_empty_tickets(self):
        reporter, sheet, sla, _ = _make_reporter()
        sheet.get_all_tickets.return_value = []
        sheet.get_all_tickets_today.return_value = []

        stats = reporter.generate_stats()

        assert stats["received_today"] == 0
        assert stats["total_open"] == 0
        assert stats["closed_today"] == 0
        assert stats["sla_breaches"] == 0
        assert stats["unassigned"] == 0

    def test_counts_open_tickets(self):
        reporter, sheet, sla, _ = _make_reporter()
        sheet.get_all_tickets.return_value = [
            {"Status": "New", "Assigned To": "Shreyas", "Timestamp": "07 Mar 2026, 10:00 AM"},
            {"Status": "In Progress", "Assigned To": "EA", "Timestamp": "07 Mar 2026, 11:00 AM"},
            {"Status": "Closed", "Assigned To": "Shreyas", "Timestamp": "07 Mar 2026, 09:00 AM"},
        ]
        sheet.get_all_tickets_today.return_value = sheet.get_all_tickets.return_value

        stats = reporter.generate_stats()

        assert stats["total_open"] == 2
        assert stats["received_today"] == 3
        assert stats["closed_today"] == 1

    def test_counts_unassigned(self):
        reporter, sheet, sla, _ = _make_reporter()
        sheet.get_all_tickets.return_value = [
            {"Status": "New", "Assigned To": "", "Timestamp": "07 Mar 2026, 10:00 AM"},
            {"Status": "New", "Assigned To": "  ", "Timestamp": "07 Mar 2026, 10:00 AM"},
            {"Status": "New", "Assigned To": "Shreyas", "Timestamp": "07 Mar 2026, 10:00 AM"},
        ]
        sheet.get_all_tickets_today.return_value = []

        stats = reporter.generate_stats()

        assert stats["unassigned"] == 2

    def test_counts_breaches(self):
        reporter, sheet, sla, _ = _make_reporter()
        sheet.get_all_tickets.return_value = []
        sheet.get_all_tickets_today.return_value = []
        sla.get_breached_tickets.return_value = [
            {"Ticket #": "INF-0001", "hours_overdue": 3.5},
            {"Ticket #": "INF-0002", "hours_overdue": 1.0},
        ]

        stats = reporter.generate_stats()

        assert stats["sla_breaches"] == 2


class TestFallbackPlainText:
    """Test _fallback_plain_text static method."""

    def test_contains_all_stats(self):
        stats = {
            "date": "07 Mar 2026",
            "received_today": 5,
            "closed_today": 2,
            "total_open": 10,
            "sla_breaches": 1,
            "unassigned": 3,
            "sheet_url": "https://sheets.test",
        }
        text = EODReporter._fallback_plain_text(stats)

        assert "07 Mar 2026" in text
        assert "5" in text
        assert "10" in text
        assert "sheets.test" in text


class TestSendReport:
    """Test send_report orchestration."""

    @patch.object(EODReporter, "_send_email")
    @patch.object(EODReporter, "_get_gmail_service")
    def test_calls_chat_and_email(self, mock_gmail, mock_send_email, mock_sheet, mock_chat):
        reporter, _, _, chat = _make_reporter(mock_sheet=mock_sheet, mock_chat=mock_chat)
        reporter.sheet.get_all_tickets.return_value = []
        reporter.sheet.get_all_tickets_today.return_value = []

        reporter.send_report()

        chat.notify_eod_summary.assert_called_once()
        mock_send_email.assert_called_once()

    @patch.object(EODReporter, "_send_email")
    @patch.object(EODReporter, "_get_gmail_service")
    def test_respects_email_disabled_flag(self, mock_gmail, mock_send_email, mock_sheet, mock_chat):
        config = {
            "eod": {"recipients": ["admin@test.com"], "send_hour": 19, "send_minute": 0},
            "admin": {"email": "admin@test.com"},
            "google_sheets": {"spreadsheet_id": "test-sheet-id", "agent_config_tab": "Agent Config"},
            "feature_flags": {"eod_email_enabled": False},
        }
        reporter, _, _, chat = _make_reporter(config=config, mock_sheet=mock_sheet, mock_chat=mock_chat)
        reporter.sheet.get_all_tickets.return_value = []
        reporter.sheet.get_all_tickets_today.return_value = []

        reporter.send_report()

        chat.notify_eod_summary.assert_called_once()
        mock_send_email.assert_not_called()


class TestConfigurableSender:
    """Test EOD sender email configuration."""

    def test_uses_eod_sender_when_set(self):
        config = {
            "eod": {"recipients": ["admin@test.com"], "send_hour": 19, "send_minute": 0,
                    "sender_email": "agent@vidarbhainfotech.com"},
            "admin": {"email": "shreyas@vidarbhainfotech.com"},
            "google_sheets": {"spreadsheet_id": "test-sheet-id", "agent_config_tab": "Agent Config"},
            "feature_flags": {"eod_email_enabled": True},
        }
        reporter, _, _, _ = _make_reporter(config=config)
        assert reporter.sender_email == "agent@vidarbhainfotech.com"

    def test_falls_back_to_admin_email(self):
        config = {
            "eod": {"recipients": ["admin@test.com"], "send_hour": 19, "send_minute": 0},
            "admin": {"email": "shreyas@vidarbhainfotech.com"},
            "google_sheets": {"spreadsheet_id": "test-sheet-id", "agent_config_tab": "Agent Config"},
            "feature_flags": {"eod_email_enabled": True},
        }
        reporter, _, _, _ = _make_reporter(config=config)
        assert reporter.sender_email == "shreyas@vidarbhainfotech.com"
