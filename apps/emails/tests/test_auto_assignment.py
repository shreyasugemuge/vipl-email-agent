"""Tests for assignment rule models, SLA config model, category visibility model,
auto-assign batch job, and inline auto-assign in pipeline."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from django.db import IntegrityError
from django.utils import timezone as dj_timezone

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    AssignmentRule,
    CategoryVisibility,
    Email,
    SLAConfig,
    Thread,
)
from apps.emails.services.dtos import TriageResult
from conftest import create_email


# ===========================================================================
# AssignmentRule Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestAssignmentRuleModel:
    """Test AssignmentRule model creation and constraints."""

    def test_create_rule(self, member_user):
        """Can create an assignment rule."""
        rule = AssignmentRule.objects.create(
            category="Sales Lead",
            assignee=member_user,
            priority_order=1,
        )
        assert rule.pk is not None
        assert rule.is_active is True

    def test_unique_together(self, member_user):
        """Cannot create duplicate category+assignee pair."""
        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=1,
        )
        with pytest.raises(IntegrityError):
            AssignmentRule.objects.create(
                category="Sales Lead", assignee=member_user, priority_order=2,
            )

    def test_ordering(self, admin_user, member_user):
        """Rules are ordered by category, then priority_order."""
        r2 = AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=2,
        )
        r1 = AssignmentRule.objects.create(
            category="Sales Lead", assignee=admin_user, priority_order=1,
        )
        rules = list(AssignmentRule.objects.filter(category="Sales Lead"))
        assert rules[0] == r1
        assert rules[1] == r2


# ===========================================================================
# SLAConfig Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestSLAConfigModel:
    """Test SLAConfig model creation and constraints."""

    def test_create_config(self):
        """Can create SLA config."""
        config = SLAConfig.objects.create(
            priority="MEDIUM", category="Sales Lead",
            ack_hours=1.0, respond_hours=8.0,
        )
        assert config.pk is not None
        assert config.ack_hours == 1.0

    def test_unique_together(self):
        """Cannot create duplicate priority+category pair."""
        SLAConfig.objects.create(
            priority="MEDIUM", category="Sales Lead",
            ack_hours=1.0, respond_hours=8.0,
        )
        with pytest.raises(IntegrityError):
            SLAConfig.objects.create(
                priority="MEDIUM", category="Sales Lead",
                ack_hours=2.0, respond_hours=16.0,
            )

    def test_defaults(self):
        """Default ack_hours=1.0 and respond_hours=24.0."""
        config = SLAConfig.objects.create(
            priority="LOW", category="General Inquiry",
        )
        assert config.ack_hours == 1.0
        assert config.respond_hours == 24.0


# ===========================================================================
# CategoryVisibility Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestCategoryVisibilityModel:
    """Test CategoryVisibility model creation and constraints."""

    def test_create_visibility(self, member_user):
        """Can create category visibility."""
        vis = CategoryVisibility.objects.create(
            user=member_user, category="Sales Lead",
        )
        assert vis.pk is not None

    def test_unique_together(self, member_user):
        """Cannot create duplicate user+category pair."""
        CategoryVisibility.objects.create(
            user=member_user, category="Sales Lead",
        )
        with pytest.raises(IntegrityError):
            CategoryVisibility.objects.create(
                user=member_user, category="Sales Lead",
            )


# ===========================================================================
# Auto-Assign Batch Tests
# ===========================================================================


@pytest.mark.django_db
class TestAutoAssignBatch:
    """Test auto_assign_batch service function."""

    def test_matches_rule_and_assigns(self, member_user):
        """Matches rule by category and assigns to first-priority person."""
        from apps.emails.services.assignment import auto_assign_batch

        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=1,
        )
        email = create_email(category="Sales Lead", message_id="msg_batch_1")

        count = auto_assign_batch()

        email.refresh_from_db()
        assert email.assigned_to == member_user
        assert count == 1

    def test_skips_when_no_rule(self):
        """Skips emails with no matching assignment rule."""
        from apps.emails.services.assignment import auto_assign_batch

        email = create_email(message_id="msg_batch_2", category="Vendor")

        count = auto_assign_batch()

        email.refresh_from_db()
        assert email.assigned_to is None
        assert count == 0

    def test_skips_already_assigned(self, admin_user, member_user):
        """Does not overwrite manually assigned emails."""
        from apps.emails.services.assignment import auto_assign_batch

        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=1,
        )
        email = create_email(category="Sales Lead", message_id="msg_batch_3", assigned_to=admin_user)

        count = auto_assign_batch()

        email.refresh_from_db()
        assert email.assigned_to == admin_user  # unchanged
        assert count == 0

    def test_respects_priority_order(self, admin_user, member_user):
        """Assigns to the lowest priority_order person."""
        from apps.emails.services.assignment import auto_assign_batch

        other_user = User.objects.create_user(
            username="backup", password="testpass123",
            email="backup@vidarbhainfotech.com",
        )
        AssignmentRule.objects.create(
            category="Sales Lead", assignee=other_user, priority_order=2,
        )
        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=1,
        )
        email = create_email(category="Sales Lead", message_id="msg_batch_4")

        auto_assign_batch()

        email.refresh_from_db()
        assert email.assigned_to == member_user

    def test_skips_inactive_assignees(self, member_user):
        """Skips rules where assignee is inactive."""
        from apps.emails.services.assignment import auto_assign_batch

        member_user.is_active = False
        member_user.save()
        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=1,
        )
        email = create_email(category="Sales Lead", message_id="msg_batch_5")

        count = auto_assign_batch()

        email.refresh_from_db()
        assert email.assigned_to is None
        assert count == 0

    def test_skips_inactive_rules(self, member_user):
        """Skips inactive assignment rules."""
        from apps.emails.services.assignment import auto_assign_batch

        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user,
            priority_order=1, is_active=False,
        )
        email = create_email(category="Sales Lead", message_id="msg_batch_6")

        count = auto_assign_batch()

        email.refresh_from_db()
        assert email.assigned_to is None
        assert count == 0

    def test_creates_auto_assigned_log(self, member_user):
        """Creates ActivityLog with AUTO_ASSIGNED action."""
        from apps.emails.services.assignment import auto_assign_batch

        AssignmentRule.objects.create(
            category="Sales Lead", assignee=member_user, priority_order=1,
        )
        email = create_email(category="Sales Lead", message_id="msg_batch_7")

        auto_assign_batch()

        log = ActivityLog.objects.filter(
            email=email, action=ActivityLog.Action.AUTO_ASSIGNED,
        ).first()
        assert log is not None
        assert "Sales Lead" in log.detail


# ===========================================================================
# Inline Auto-Assign Tests (pipeline _try_inline_auto_assign)
# ===========================================================================


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
def inline_assignee(db):
    return User.objects.create_user(
        username="inline_assignee",
        email="inline_assignee@vidarbhainfotech.com",
        password="test1234",
        first_name="Test",
        last_name="Assignee",
        is_active=True,
    )


@pytest.fixture
def inline_thread(db):
    return Thread.objects.create(
        gmail_thread_id="thread-inline-auto-1",
        subject="Auto-assign test",
        category="billing",
        priority="HIGH",
        ai_confidence="HIGH",
    )


@pytest.fixture
def inline_rule(db, inline_assignee):
    return AssignmentRule.objects.create(
        category="billing",
        assignee=inline_assignee,
        priority_order=0,
        is_active=True,
    )


@pytest.fixture
def enable_auto_assign(db):
    """Set auto-assign threshold to HIGH (enabled)."""
    SystemConfig.objects.update_or_create(
        key="auto_assign_confidence_tier",
        defaults={"value": "HIGH", "value_type": "STR"},
    )


def _make_inline_triage(confidence="HIGH", category="billing", is_spam=False):
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

    def test_high_confidence_matching_rule_auto_assigns(self, inline_thread, inline_rule, inline_assignee, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to == inline_assignee
        assert inline_thread.is_auto_assigned is True
        assert inline_thread.assigned_at is not None

    def test_medium_confidence_no_auto_assign(self, inline_thread, inline_rule, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="MEDIUM", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None
        assert inline_thread.is_auto_assigned is False

    def test_low_confidence_no_auto_assign(self, inline_thread, inline_rule, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="LOW", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None
        assert inline_thread.is_auto_assigned is False

    def test_high_confidence_no_matching_rule(self, inline_thread, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None

    def test_already_assigned_thread_not_overwritten(self, inline_thread, inline_rule, inline_assignee, enable_auto_assign):
        """Optimistic locking: thread already assigned should not be overwritten."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        other_user = User.objects.create_user(
            username="other_inline", email="other_inline@test.com", password="test1234", is_active=True,
        )
        inline_thread.assigned_to = other_user
        inline_thread.save(update_fields=["assigned_to"])

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to == other_user  # Not overwritten

    def test_threshold_disabled_no_auto_assign(self, inline_thread, inline_rule):
        """When threshold is 100 (disabled, the default), no auto-assign happens."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None

    def test_creates_assignment_feedback(self, inline_thread, inline_rule, inline_assignee, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        feedback = AssignmentFeedback.objects.filter(thread=inline_thread).first()
        assert feedback is not None
        assert feedback.action == AssignmentFeedback.FeedbackAction.AUTO_ASSIGNED
        assert feedback.suggested_user == inline_assignee
        assert feedback.actual_user == inline_assignee
        assert feedback.confidence_at_time == "HIGH"
        assert feedback.user_who_acted is None

    def test_creates_activity_log(self, inline_thread, inline_rule, inline_assignee, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        log = ActivityLog.objects.filter(
            thread=inline_thread, action=ActivityLog.Action.AUTO_ASSIGNED,
        ).first()
        assert log is not None
        assert "billing" in log.detail
        assert inline_assignee.get_full_name() in log.new_value or inline_assignee.username in log.new_value

    def test_sets_is_auto_assigned_true(self, inline_thread, inline_rule, inline_assignee, enable_auto_assign):
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.is_auto_assigned is True

    def test_failure_does_not_crash_pipeline(self, inline_thread, inline_rule, enable_auto_assign):
        """Auto-assign errors should be swallowed, not crash the pipeline."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        with patch("apps.emails.services.pipeline.AssignmentRule.objects") as mock_qs:
            mock_qs.filter.side_effect = Exception("DB error")
            triage = _make_inline_triage(confidence="HIGH", category="billing")
            # Should not raise
            _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None  # Not assigned due to error

    def test_spam_email_not_auto_assigned(self, inline_thread, inline_rule, enable_auto_assign):
        """Spam triage results should never trigger auto-assign."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        triage = _make_inline_triage(confidence="HIGH", category="billing", is_spam=True)
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None

    def test_inactive_assignee_rule_skipped(self, inline_thread, inline_assignee, enable_auto_assign):
        """Rule with inactive assignee should not match."""
        from apps.emails.services.pipeline import _try_inline_auto_assign

        inline_assignee.is_active = False
        inline_assignee.save()
        AssignmentRule.objects.create(
            category="billing", assignee=inline_assignee, priority_order=0, is_active=True,
        )

        triage = _make_inline_triage(confidence="HIGH", category="billing")
        _try_inline_auto_assign(inline_thread, triage)

        inline_thread.refresh_from_db()
        assert inline_thread.assigned_to is None
