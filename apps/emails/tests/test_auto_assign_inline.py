"""Tests for inline auto-assign in pipeline (02-02).

Tests the is_auto_assigned field and the _try_inline_auto_assign function
that runs during process_single_email for HIGH confidence threads.
"""

from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    AssignmentRule,
    Email,
    Thread,
)
from apps.emails.services.dtos import TriageResult


@pytest.mark.django_db
class TestIsAutoAssignedField:
    """Test Thread.is_auto_assigned model field."""

    def test_defaults_to_false(self):
        thread = Thread(gmail_thread_id="t1", subject="Test")
        assert thread.is_auto_assigned is False

    def test_can_be_set_to_true(self):
        thread = Thread.objects.create(gmail_thread_id="t2", subject="Test")
        thread.is_auto_assigned = True
        thread.save()
        thread.refresh_from_db()
        assert thread.is_auto_assigned is True


@pytest.fixture
def assignee(db):
    return User.objects.create_user(
        username="assignee",
        email="assignee@vidarbhainfotech.com",
        password="test1234",
        first_name="Test",
        last_name="Assignee",
        is_active=True,
    )


@pytest.fixture
def thread(db):
    return Thread.objects.create(
        gmail_thread_id="thread-auto-1",
        subject="Auto-assign test",
        category="billing",
        priority="HIGH",
        ai_confidence="HIGH",
    )


@pytest.fixture
def rule(db, assignee):
    return AssignmentRule.objects.create(
        category="billing",
        assignee=assignee,
        priority_order=0,
        is_active=True,
    )


def _make_triage(confidence="HIGH", category="billing", is_spam=False):
    return TriageResult(
        category=category,
        priority="HIGH",
        summary="Test summary",
        confidence=confidence,
        is_spam=is_spam,
    )


@pytest.mark.django_db
class TestTryInlineAutoAssign:
    """Test _try_inline_auto_assign function."""

    def test_high_confidence_matching_rule_auto_assigns(self, thread, rule, assignee):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to == assignee
        assert thread.is_auto_assigned is True
        assert thread.assigned_at is not None

    def test_medium_confidence_no_auto_assign(self, thread, rule):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="MEDIUM", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None
        assert thread.is_auto_assigned is False

    def test_low_confidence_no_auto_assign(self, thread, rule):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="LOW", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None
        assert thread.is_auto_assigned is False

    def test_high_confidence_no_matching_rule(self, thread):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        # No rule for "billing" category
        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None

    def test_already_assigned_thread_not_overwritten(self, thread, rule, assignee):
        """Optimistic locking: thread already assigned should not be overwritten."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        other_user = User.objects.create_user(
            username="other", email="other@test.com", password="test1234", is_active=True,
        )
        thread.assigned_to = other_user
        thread.save(update_fields=["assigned_to"])

        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to == other_user  # Not overwritten

    def test_threshold_disabled_no_auto_assign(self, thread, rule):
        """When threshold is 100 (disabled), no auto-assign happens."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        with patch("apps.emails.services.pipeline.SystemConfig.get") as mock_get:
            mock_get.return_value = "100"
            triage = _make_triage(confidence="HIGH", category="billing")
            _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None

    def test_creates_assignment_feedback(self, thread, rule, assignee):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        feedback = AssignmentFeedback.objects.filter(thread=thread).first()
        assert feedback is not None
        assert feedback.action == AssignmentFeedback.FeedbackAction.AUTO_ASSIGNED
        assert feedback.suggested_user == assignee
        assert feedback.actual_user == assignee
        assert feedback.confidence_at_time == "HIGH"
        assert feedback.user_who_acted is None

    def test_creates_activity_log(self, thread, rule, assignee):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        log = ActivityLog.objects.filter(
            thread=thread, action=ActivityLog.Action.AUTO_ASSIGNED,
        ).first()
        assert log is not None
        assert "billing" in log.detail
        assert assignee.get_full_name() in log.new_value or assignee.username in log.new_value

    def test_sets_is_auto_assigned_true(self, thread, rule, assignee):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.is_auto_assigned is True

    def test_failure_does_not_crash_pipeline(self, thread, rule):
        """Auto-assign errors should be swallowed, not crash the pipeline."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        with patch("apps.emails.services.pipeline.AssignmentRule.objects") as mock_qs:
            mock_qs.filter.side_effect = Exception("DB error")
            triage = _make_triage(confidence="HIGH", category="billing")
            # Should not raise
            _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None  # Not assigned due to error

    def test_spam_email_not_auto_assigned(self, thread, rule):
        """Spam triage results should never trigger auto-assign."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_triage(confidence="HIGH", category="billing", is_spam=True)
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None

    def test_inactive_assignee_rule_skipped(self, thread, assignee):
        """Rule with inactive assignee should not match."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        assignee.is_active = False
        assignee.save()
        AssignmentRule.objects.create(
            category="billing", assignee=assignee, priority_order=0, is_active=True,
        )

        triage = _make_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(thread, triage)

        thread.refresh_from_db()
        assert thread.assigned_to is None
