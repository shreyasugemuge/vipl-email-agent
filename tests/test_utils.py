"""Tests for agent/utils.py — pure functions, no external services needed."""

import pytz
from agent.utils import parse_sheet_datetime, IST, SHEET_DATETIME_FORMAT


class TestParseSheetDatetime:
    """Test parse_sheet_datetime with various input formats."""

    def test_standard_format(self):
        result = parse_sheet_datetime("13 Feb 2026, 02:30 PM")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 13
        assert result.hour == 14
        assert result.minute == 30
        assert result.tzinfo is not None

    def test_with_ist_suffix(self):
        result = parse_sheet_datetime("13 Feb 2026, 02:30 PM IST")
        assert result is not None
        assert result.year == 2026
        assert result.hour == 14

    def test_with_ist_lowercase(self):
        result = parse_sheet_datetime("13 Feb 2026, 02:30 PM ist")
        assert result is not None
        assert result.year == 2026

    def test_iso_format(self):
        result = parse_sheet_datetime("2026-02-13 14:30:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.hour == 14

    def test_empty_string_returns_none(self):
        assert parse_sheet_datetime("") is None

    def test_none_input_returns_none(self):
        assert parse_sheet_datetime(None) is None

    def test_garbage_returns_none(self):
        assert parse_sheet_datetime("not-a-date") is None

    def test_whitespace_handling(self):
        result = parse_sheet_datetime("  13 Feb 2026, 02:30 PM  ")
        assert result is not None

    def test_result_is_ist_localized(self):
        result = parse_sheet_datetime("13 Feb 2026, 02:30 PM")
        assert result.tzinfo is not None
        assert str(result.tzinfo) == "Asia/Kolkata"

    def test_am_time(self):
        result = parse_sheet_datetime("07 Mar 2026, 09:00 AM")
        assert result is not None
        assert result.hour == 9
