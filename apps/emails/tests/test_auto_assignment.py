"""Tests for assignment rule models, SLA config model, and category visibility model."""

import pytest
from datetime import datetime, timezone

from django.db import IntegrityError

from apps.accounts.models import User
from apps.emails.models import AssignmentRule, CategoryVisibility, Email, SLAConfig


def _create_email(db, **overrides):
    """Helper to create an Email record."""
    defaults = {
        "message_id": f"msg_auto_{id(overrides)}",
        "from_address": "sender@example.com",
        "from_name": "Test Sender",
        "to_inbox": "info@vidarbhainfotech.com",
        "subject": "Test Subject",
        "body": "Test body",
        "received_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        "category": "Sales Lead",
        "priority": "MEDIUM",
        "processing_status": Email.ProcessingStatus.COMPLETED,
        "status": Email.Status.NEW,
    }
    defaults.update(overrides)
    return Email.objects.create(**defaults)


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
