"""Tests for AI corrections digest on triage queue."""

from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import ActivityLog, Thread


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin_digest",
        email="admin_digest@vidarbhainfotech.com",
        password="test",
        role=User.Role.ADMIN,
        is_active=True,
    )


@pytest.fixture
def member_user(db):
    return User.objects.create_user(
        username="member_digest",
        email="member_digest@vidarbhainfotech.com",
        password="test",
        role=User.Role.MEMBER,
        is_active=True,
    )


@pytest.fixture
def triage_lead_user(db):
    return User.objects.create_user(
        username="lead_digest",
        email="lead_digest@vidarbhainfotech.com",
        password="test",
        role=User.Role.TRIAGE_LEAD,
        is_active=True,
    )


@pytest.fixture
def thread(db):
    return Thread.objects.create(
        gmail_thread_id="digest_test_thread_001",
        subject="Test thread for digest",
        status=Thread.Status.NEW,
    )


def _create_log(thread, action, detail="", days_ago=0, user=None):
    """Create an ActivityLog entry with a specific created_at."""
    log = ActivityLog.objects.create(
        thread=thread,
        action=action,
        detail=detail,
        user=user,
    )
    if days_ago:
        log.created_at = timezone.now() - timedelta(days=days_ago)
        log.save(update_fields=["created_at"])
    return log


class TestGetCorrectionsDigest:
    """Tests for the get_corrections_digest() function."""

    def test_zero_counts_when_no_entries(self, db):
        from apps.emails.services.reports import get_corrections_digest

        result = get_corrections_digest()
        assert result["category_changes"] == 0
        assert result["priority_overrides"] == 0
        assert result["spam_corrections"] == 0
        assert result["total"] == 0
        assert result["top_patterns"] == []

    def test_counts_correction_actions(self, thread, admin_user):
        from apps.emails.services.reports import get_corrections_digest

        _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "General -> Govt", user=admin_user)
        _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "General -> Govt", user=admin_user)
        _create_log(thread, ActivityLog.Action.PRIORITY_CHANGED, "LOW -> HIGH", user=admin_user)
        _create_log(thread, ActivityLog.Action.SPAM_MARKED, "", user=admin_user)

        result = get_corrections_digest()
        assert result["category_changes"] == 2
        assert result["priority_overrides"] == 1
        assert result["spam_corrections"] == 1
        assert result["total"] == 4

    def test_ignores_entries_older_than_7_days(self, thread, admin_user):
        from apps.emails.services.reports import get_corrections_digest

        # Recent (within 7 days)
        _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "A -> B", days_ago=1)
        # Old (beyond 7 days)
        _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "C -> D", days_ago=10)
        _create_log(thread, ActivityLog.Action.PRIORITY_CHANGED, "LOW -> HIGH", days_ago=14)

        result = get_corrections_digest()
        assert result["category_changes"] == 1
        assert result["priority_overrides"] == 0
        assert result["total"] == 1

    def test_top_patterns_sorted_by_frequency(self, thread, admin_user):
        from apps.emails.services.reports import get_corrections_digest

        # Create patterns with different frequencies
        for _ in range(5):
            _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "General -> Govt")
        for _ in range(3):
            _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "HR -> Finance")
        for _ in range(1):
            _create_log(thread, ActivityLog.Action.PRIORITY_CHANGED, "LOW -> HIGH")

        result = get_corrections_digest()
        patterns = result["top_patterns"]
        assert len(patterns) == 3
        # Most frequent first
        assert patterns[0] == ("General -> Govt", 5)
        assert patterns[1] == ("HR -> Finance", 3)
        assert patterns[2] == ("LOW -> HIGH", 1)

    def test_total_is_sum_of_all_types(self, thread, admin_user):
        from apps.emails.services.reports import get_corrections_digest

        _create_log(thread, ActivityLog.Action.CATEGORY_CHANGED, "A -> B")
        _create_log(thread, ActivityLog.Action.PRIORITY_CHANGED, "LOW -> HIGH")
        _create_log(thread, ActivityLog.Action.SPAM_MARKED, "")

        result = get_corrections_digest()
        expected = result["category_changes"] + result["priority_overrides"] + result["spam_corrections"]
        assert result["total"] == expected
        assert result["total"] == 3

    def test_view_includes_digest_for_admin_on_triage_queue(self, admin_user, client, thread):
        client.force_login(admin_user)
        response = client.get("/emails/?view=unassigned")
        assert response.status_code == 200
        assert "corrections_digest" in response.context

    def test_view_excludes_digest_for_member(self, member_user, client, thread):
        client.force_login(member_user)
        response = client.get("/emails/?view=unassigned")
        assert response.status_code == 200
        # Member should not have corrections_digest in context
        assert response.context.get("corrections_digest") is None
