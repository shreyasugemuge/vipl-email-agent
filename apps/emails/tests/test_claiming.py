"""Tests for email claiming service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from apps.accounts.models import User
from apps.emails.models import ActivityLog, AssignmentRule, CategoryVisibility, Email


def _create_email(db, **overrides):
    """Helper to create an Email record."""
    defaults = {
        "message_id": f"msg_claim_{id(overrides)}",
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


@pytest.mark.django_db
class TestClaimEmail:
    """Test claim_email service function."""

    def test_successful_claim(self, member_user):
        """Claim sets assignee and creates activity log."""
        from apps.emails.services.assignment import claim_email

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        email = _create_email(None, message_id="msg_claim_1")

        result = claim_email(email, member_user)

        result.refresh_from_db()
        assert result.assigned_to == member_user
        log = ActivityLog.objects.filter(email=email, action=ActivityLog.Action.CLAIMED).first()
        assert log is not None

    def test_raises_value_error_when_already_assigned(self, admin_user, member_user):
        """Raises ValueError if email already assigned."""
        from apps.emails.services.assignment import claim_email

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        email = _create_email(None, message_id="msg_claim_2", assigned_to=admin_user)

        with pytest.raises(ValueError, match="already assigned"):
            claim_email(email, member_user)

    def test_raises_permission_error_without_visibility(self, member_user):
        """Raises PermissionError if member lacks category visibility."""
        from apps.emails.services.assignment import claim_email

        email = _create_email(None, message_id="msg_claim_3")

        with pytest.raises(PermissionError, match="visibility"):
            claim_email(email, member_user)

    def test_admin_bypasses_visibility(self, admin_user):
        """Admin can claim without CategoryVisibility."""
        from apps.emails.services.assignment import claim_email

        email = _create_email(None, message_id="msg_claim_4")

        result = claim_email(email, admin_user)
        result.refresh_from_db()
        assert result.assigned_to == admin_user

    def test_claimed_action_in_log(self, member_user):
        """ActivityLog shows CLAIMED action (not ASSIGNED)."""
        from apps.emails.services.assignment import claim_email

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        email = _create_email(None, message_id="msg_claim_5")

        claim_email(email, member_user)

        logs = ActivityLog.objects.filter(email=email)
        actions = [log.action for log in logs]
        assert ActivityLog.Action.CLAIMED in actions
