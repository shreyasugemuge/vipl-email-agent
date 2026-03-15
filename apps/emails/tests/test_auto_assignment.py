"""Tests for assignment rule models, SLA config model, category visibility model,
and auto-assign batch job."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from django.db import IntegrityError

from apps.accounts.models import User
from apps.emails.models import ActivityLog, AssignmentRule, CategoryVisibility, Email, SLAConfig
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
