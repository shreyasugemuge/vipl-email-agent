"""Tests for AI performance calibration and parse_recipients template filter."""

import pytest
from datetime import datetime, timezone as dt_tz

from apps.emails.models import ActivityLog, AssignmentFeedback, Thread
from apps.emails.templatetags.email_tags import parse_recipients
from conftest import create_email, create_thread


# ===========================================================================
# Template filter tests -- parse_recipients
# ===========================================================================


class TestParseRecipients:

    def test_single_address(self):
        headers = {"to": "alice@example.com"}
        result = parse_recipients(headers, "to")
        assert len(result) == 1
        assert result[0]["address"] == "alice@example.com"

    def test_address_with_name(self):
        headers = {"to": "Alice Smith <alice@example.com>"}
        result = parse_recipients(headers, "to")
        assert len(result) == 1
        assert result[0]["name"] == "Alice Smith"
        assert result[0]["address"] == "alice@example.com"

    def test_multiple_addresses(self):
        headers = {"to": "Alice <alice@a.com>, Bob <bob@b.com>, carol@c.com"}
        result = parse_recipients(headers, "to")
        assert len(result) == 3
        assert result[0]["name"] == "Alice"
        assert result[1]["address"] == "bob@b.com"
        assert result[2]["address"] == "carol@c.com"

    def test_cc_field(self):
        headers = {"cc": "manager@company.com"}
        result = parse_recipients(headers, "cc")
        assert len(result) == 1
        assert result[0]["address"] == "manager@company.com"

    def test_empty_header(self):
        headers = {"to": ""}
        result = parse_recipients(headers, "to")
        assert result == []

    def test_missing_header(self):
        headers = {"to": "alice@a.com"}
        result = parse_recipients(headers, "cc")
        assert result == []

    def test_empty_dict(self):
        result = parse_recipients({}, "to")
        assert result == []

    def test_none_input(self):
        result = parse_recipients(None, "to")
        assert result == []

    def test_non_dict_input(self):
        result = parse_recipients("not a dict", "to")
        assert result == []


# ===========================================================================
# AI Performance report tests
# ===========================================================================


@pytest.mark.django_db
class TestAIPerformanceData:

    def _make_thread(self, confidence="HIGH", cat_overridden=False, pri_overridden=False, **kwargs):
        t = create_thread(
            ai_confidence=confidence,
            category_overridden=cat_overridden,
            priority_overridden=pri_overridden,
            **kwargs,
        )
        return t

    def test_calibration_per_tier(self):
        from apps.emails.services.reports import get_ai_performance_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        # 3 HIGH: 2 accurate, 1 overridden
        self._make_thread("HIGH")
        self._make_thread("HIGH")
        self._make_thread("HIGH", cat_overridden=True)

        # 2 MEDIUM: 1 accurate, 1 overridden
        self._make_thread("MEDIUM")
        self._make_thread("MEDIUM", pri_overridden=True)

        # 1 LOW: 0 accurate, 1 overridden
        self._make_thread("LOW", cat_overridden=True)

        result = get_ai_performance_data(start, end)

        assert result["calibration"]["HIGH"]["total"] == 3
        assert result["calibration"]["HIGH"]["accurate"] == 2
        assert result["calibration"]["HIGH"]["accuracy_pct"] == 66.7

        assert result["calibration"]["MEDIUM"]["total"] == 2
        assert result["calibration"]["MEDIUM"]["accurate"] == 1
        assert result["calibration"]["MEDIUM"]["accuracy_pct"] == 50.0

        assert result["calibration"]["LOW"]["total"] == 1
        assert result["calibration"]["LOW"]["overridden"] == 1
        assert result["calibration"]["LOW"]["accuracy_pct"] == 0

    def test_overall_accuracy(self):
        from apps.emails.services.reports import get_ai_performance_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        # 4 threads: 3 accurate, 1 overridden -> 75%
        self._make_thread("HIGH")
        self._make_thread("HIGH")
        self._make_thread("MEDIUM")
        self._make_thread("LOW", cat_overridden=True)

        result = get_ai_performance_data(start, end)
        assert result["overall_accuracy"] == 75.0
        assert result["total_analyzed"] == 4

    def test_empty_data(self):
        from apps.emails.services.reports import get_ai_performance_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        result = get_ai_performance_data(start, end)
        assert result["overall_accuracy"] == 0
        assert result["total_analyzed"] == 0
        assert result["calibration"]["HIGH"]["total"] == 0
        assert result["assignment"]["total"] == 0
        assert result["corrections"]["total"] == 0

    def test_correction_counts(self):
        from apps.emails.services.reports import get_ai_performance_data
        from apps.accounts.models import User

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        user = User.objects.create_user(username="tester", password="pass")
        t = self._make_thread("HIGH", cat_overridden=True)

        ActivityLog.objects.create(
            thread=t, user=user,
            action=ActivityLog.Action.CATEGORY_CHANGED,
            old_value="Sales Lead", new_value="Support Request",
        )
        ActivityLog.objects.create(
            thread=t, user=user,
            action=ActivityLog.Action.PRIORITY_CHANGED,
            old_value="HIGH", new_value="MEDIUM",
        )

        result = get_ai_performance_data(start, end)
        assert result["corrections"]["category_changes"] == 1
        assert result["corrections"]["priority_changes"] == 1
        assert result["corrections"]["total"] == 2

    def test_model_comparison(self):
        from apps.emails.services.reports import get_ai_performance_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        # Thread with haiku email (accurate)
        t1 = self._make_thread("HIGH")
        create_email(thread=t1, ai_model_used="claude-haiku-4-5-20251001")

        # Thread with haiku email (overridden)
        t2 = self._make_thread("MEDIUM", cat_overridden=True)
        create_email(thread=t2, ai_model_used="claude-haiku-4-5-20251001")

        # Thread with sonnet email (accurate)
        t3 = self._make_thread("HIGH")
        create_email(thread=t3, ai_model_used="claude-sonnet-4-5-20250929")

        result = get_ai_performance_data(start, end)
        assert "Haiku" in result["model_comparison"]
        assert result["model_comparison"]["Haiku"]["total"] == 2
        assert "Sonnet" in result["model_comparison"]
        assert result["model_comparison"]["Sonnet"]["total"] == 1
