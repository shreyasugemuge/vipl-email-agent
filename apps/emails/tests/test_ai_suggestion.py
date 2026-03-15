"""Tests for AI workload context injection and structured assignee suggestion parsing."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from apps.accounts.models import User
from apps.emails.models import Email
from apps.emails.services.dtos import TriageResult
from conftest import create_email


# ===========================================================================
# Team Workload Tests
# ===========================================================================


@pytest.mark.django_db
class TestGetTeamWorkload:
    """Test _get_team_workload function."""

    def test_returns_correct_counts(self, admin_user, member_user):
        """Returns each active user with their open email count."""
        from apps.emails.services.ai_processor import _get_team_workload

        # Assign 2 open emails to member
        create_email(message_id="msg_wl_1", assigned_to=member_user, status="new", category="Sales Lead")
        create_email(message_id="msg_wl_2", assigned_to=member_user, status="acknowledged", category="Sales Lead")
        # Closed email should not count
        create_email(message_id="msg_wl_3", assigned_to=member_user, status="closed", category="Sales Lead")

        workload = _get_team_workload()
        member_entry = next((w for w in workload if w["email"] == member_user.email), None)
        assert member_entry is not None
        assert member_entry["open_count"] == 2

    def test_handles_no_users(self):
        """Returns empty list when no active users exist."""
        from apps.emails.services.ai_processor import _get_team_workload

        workload = _get_team_workload()
        assert workload == []

    def test_excludes_inactive_users(self, member_user):
        """Does not include inactive users."""
        from apps.emails.services.ai_processor import _get_team_workload

        member_user.is_active = False
        member_user.save()

        workload = _get_team_workload()
        emails_in_workload = [w["email"] for w in workload]
        assert member_user.email not in emails_in_workload


# ===========================================================================
# Build User Message Tests
# ===========================================================================


@pytest.mark.django_db
class TestBuildUserMessage:
    """Test _build_user_message workload section."""

    def test_workload_section_appended(self, member_user):
        """User message includes Team workload section when team exists."""
        from apps.emails.services.ai_processor import AIProcessor
        from apps.emails.services.dtos import EmailMessage

        create_email(message_id="msg_bum_1", assigned_to=member_user, status="new", category="Sales Lead")

        processor = AIProcessor.__new__(AIProcessor)
        email_msg = EmailMessage(
            thread_id="t1", message_id="m1", inbox="info@vidarbhainfotech.com",
            sender_name="Test", sender_email="test@example.com",
            subject="Test", body="Test body",
            timestamp=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

        message = processor._build_user_message(email_msg)
        assert "TEAM WORKLOAD" in message or "Team workload" in message
        assert "open email" in message.lower()

    def test_empty_workload_handled(self):
        """When no team data, shows 'No team data available'."""
        from apps.emails.services.ai_processor import AIProcessor
        from apps.emails.services.dtos import EmailMessage

        processor = AIProcessor.__new__(AIProcessor)
        email_msg = EmailMessage(
            thread_id="t1", message_id="m1", inbox="info@vidarbhainfotech.com",
            sender_name="Test", sender_email="test@example.com",
            subject="Test", body="Test body",
            timestamp=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

        message = processor._build_user_message(email_msg)
        assert "No team data available" in message


# ===========================================================================
# Parse Structured Suggestion Tests
# ===========================================================================


class TestParseStructuredSuggestion:
    """Test parsing of structured assignee suggestion from Claude response."""

    def test_dict_format_parsed(self):
        """Dict format {name, reason} parsed correctly."""
        from apps.emails.services.ai_processor import _parse_suggested_assignee

        raw = {"name": "Rahul", "reason": "Sales expert with lowest workload"}
        result = _parse_suggested_assignee(raw)
        assert result["name"] == "Rahul"
        assert result["reason"] == "Sales expert with lowest workload"

    def test_string_format_backward_compat(self):
        """String format converted to dict for backward compat."""
        from apps.emails.services.ai_processor import _parse_suggested_assignee

        result = _parse_suggested_assignee("Rahul")
        assert result["name"] == "Rahul"
        assert result["reason"] == ""

    def test_empty_suggestion_handled(self):
        """Empty or None returns empty dict."""
        from apps.emails.services.ai_processor import _parse_suggested_assignee

        assert _parse_suggested_assignee("") == {}
        assert _parse_suggested_assignee(None) == {}


# ===========================================================================
# TriageResult Detail Tests
# ===========================================================================


class TestTriageResultDetail:
    """Test suggested_assignee_detail field on TriageResult."""

    def test_detail_populated(self):
        """suggested_assignee_detail can hold structured data."""
        result = TriageResult(
            suggested_assignee="Rahul",
            suggested_assignee_detail={"name": "Rahul", "reason": "Expert"},
        )
        assert result.suggested_assignee_detail["name"] == "Rahul"
        assert result.suggested_assignee == "Rahul"

    def test_detail_defaults_empty(self):
        """suggested_assignee_detail defaults to empty dict."""
        result = TriageResult()
        assert result.suggested_assignee_detail == {}
