"""Tests for agent/sheet_logger.py — all mocked, no real Google Sheets API."""

from unittest.mock import patch, MagicMock
from agent.sheet_logger import SheetLogger


def _make_logger(ticket_values=None):
    """Create a SheetLogger with mocked Google APIs."""
    with patch("agent.sheet_logger.service_account.Credentials.from_service_account_file"), \
         patch("agent.sheet_logger.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_sheets = MagicMock()
        mock_service.spreadsheets.return_value = mock_sheets

        # Mock _load_ticket_counts
        values = ticket_values or []
        mock_sheets.values.return_value.get.return_value.execute.return_value = {"values": values}

        logger = SheetLogger("/tmp/fake-sa.json", "test-sheet-id", {})
        return logger, mock_sheets


class TestTicketNumbering:
    """Test _next_ticket_number for various inboxes."""

    def test_info_inbox_prefix(self):
        logger, _ = _make_logger()
        assert logger._next_ticket_number("info@vidarbhainfotech.com") == "INF-0001"
        assert logger._next_ticket_number("info@vidarbhainfotech.com") == "INF-0002"

    def test_sales_inbox_prefix(self):
        logger, _ = _make_logger()
        assert logger._next_ticket_number("sales@vidarbhainfotech.com") == "SAL-0001"

    def test_support_inbox_prefix(self):
        logger, _ = _make_logger()
        assert logger._next_ticket_number("support@vidarbhainfotech.com") == "SUP-0001"

    def test_unknown_inbox_defaults_to_inf(self):
        logger, _ = _make_logger()
        assert logger._next_ticket_number("random@test.com") == "INF-0001"

    def test_continues_from_existing_counts(self):
        existing = [["INF-0010"], ["INF-0005"], ["SAL-0003"]]
        logger, _ = _make_logger(ticket_values=existing)
        assert logger._next_ticket_number("info@vidarbhainfotech.com") == "INF-0011"
        assert logger._next_ticket_number("sales@vidarbhainfotech.com") == "SAL-0004"

    def test_independent_counters(self):
        logger, _ = _make_logger()
        logger._next_ticket_number("info@test.com")      # INF-0001
        logger._next_ticket_number("sales@test.com")     # SAL-0001
        assert logger._next_ticket_number("info@test.com") == "INF-0002"
        assert logger._next_ticket_number("sales@test.com") == "SAL-0002"


class TestExtractRowNumber:
    """Test _extract_row_number static method."""

    def test_standard_range(self):
        assert SheetLogger._extract_row_number("'Email Log'!A5:U5") == 5

    def test_large_row(self):
        assert SheetLogger._extract_row_number("'Email Log'!A1234:U1234") == 1234

    def test_no_match_returns_none(self):
        assert SheetLogger._extract_row_number("invalid") is None

    def test_empty_string(self):
        assert SheetLogger._extract_row_number("") is None


class TestThreadIdCache:
    """Test is_thread_logged and thread cache."""

    def test_unknown_thread_returns_false(self):
        logger, _ = _make_logger()
        # Force a fresh cache state
        logger._thread_id_cache = set()
        logger._thread_id_cache_time = float("inf")  # Skip refresh
        assert logger.is_thread_logged("unknown_thread") is False

    def test_cached_thread_returns_true(self):
        logger, _ = _make_logger()
        logger._thread_id_cache = {"thread_abc"}
        logger._thread_id_cache_time = float("inf")
        assert logger.is_thread_logged("thread_abc") is True

    def test_add_to_cache(self):
        logger, _ = _make_logger()
        logger._thread_id_cache = set()
        logger._thread_id_cache_time = float("inf")
        logger._add_to_thread_cache("new_thread")
        assert logger.is_thread_logged("new_thread") is True


class TestGetOpenTickets:
    """Test get_open_tickets filtering."""

    def test_filters_closed_and_spam(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Ticket #", "Status"],
                ["INF-0001", "New"],
                ["INF-0002", "Closed"],
                ["INF-0003", "Spam"],
                ["INF-0004", "In Progress"],
            ]
        }
        tickets = logger.get_open_tickets()
        ticket_ids = [t["Ticket #"] for t in tickets]
        assert "INF-0001" in ticket_ids
        assert "INF-0004" in ticket_ids
        assert "INF-0002" not in ticket_ids
        assert "INF-0003" not in ticket_ids

    def test_empty_sheet(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {"values": []}
        assert logger.get_open_tickets() == []


class TestUpdateSlaStatus:
    """Test update_sla_status writes to correct row."""

    def test_updates_correct_row(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [["Ticket #"], ["INF-0001"], ["INF-0002"], ["INF-0003"]]
        }
        logger.update_sla_status("INF-0002", "Breached")
        mock_sheets.values.return_value.update.assert_called()
        call_args = mock_sheets.values.return_value.update.call_args
        assert "M3" in call_args.kwargs.get("range", call_args[1].get("range", ""))
        assert call_args.kwargs.get("body", call_args[1].get("body", {}))["values"] == [["Breached"]]

    def test_no_match_no_error(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [["Ticket #"], ["INF-0001"]]
        }
        logger.update_sla_status("INF-9999", "Breached")  # Should not raise


class TestDeadLetterRetry:
    """Test dead letter retry methods."""

    def test_get_failed_triages_excludes_success(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Timestamp", "Inbox", "Sender", "Subject", "Error", "Thread ID",
                 "Retry Count", "Last Retry At", "Retry Status"],
                ["2026-03-01 10:00:00", "info@test.com", "a@b.com", "Test", "err",
                 "thread1", "0", "", ""],
                ["2026-03-01 10:00:00", "info@test.com", "a@b.com", "Done", "err",
                 "thread2", "1", "", "Success"],
            ]
        }
        eligible = logger.get_failed_triages_for_retry()
        assert len(eligible) == 1
        assert eligible[0]["Thread ID"] == "thread1"

    def test_get_failed_triages_excludes_exhausted(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Timestamp", "Inbox", "Sender", "Subject", "Error", "Thread ID",
                 "Retry Count", "Last Retry At", "Retry Status"],
                ["2026-03-01 10:00:00", "info@test.com", "a@b.com", "Exhausted", "err",
                 "thread3", "3", "", "Exhausted"],
            ]
        }
        eligible = logger.get_failed_triages_for_retry()
        assert len(eligible) == 0

    def test_get_failed_triages_excludes_max_retries(self):
        logger, mock_sheets = _make_logger()
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Timestamp", "Inbox", "Sender", "Subject", "Error", "Thread ID",
                 "Retry Count", "Last Retry At", "Retry Status"],
                ["2026-03-01 10:00:00", "info@test.com", "a@b.com", "Max", "err",
                 "thread4", "3", "", "Retry 3 failed"],
            ]
        }
        eligible = logger.get_failed_triages_for_retry()
        assert len(eligible) == 0

    def test_update_failed_triage_retry(self):
        logger, mock_sheets = _make_logger()
        logger.update_failed_triage_retry(5, 2, "Retry 2 failed")
        mock_sheets.values.return_value.update.assert_called_once()


class TestNumConfigFields:
    """Verify NUM_CONFIG_FIELDS matches actual CONFIG_FIELDS list."""

    def test_constant_matches_list(self):
        assert SheetLogger.NUM_CONFIG_FIELDS == len(SheetLogger.CONFIG_FIELDS)
