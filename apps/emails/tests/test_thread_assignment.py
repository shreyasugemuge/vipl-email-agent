"""Tests for thread-level assignment, status changes, claiming, and preview updates."""

import pytest
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from apps.accounts.models import User
from apps.emails.models import ActivityLog, CategoryVisibility, Email, Thread
from conftest import create_thread


def _create_email_on_thread(thread, **overrides):
    """Helper to create an Email linked to a thread."""
    defaults = {
        "message_id": f"msg_{id(overrides)}_{overrides.get('subject', 'test')}",
        "thread": thread,
        "gmail_thread_id": thread.gmail_thread_id,
        "from_address": "sender@example.com",
        "from_name": "Test Sender",
        "to_inbox": "info@vidarbhainfotech.com",
        "subject": "Test Email Subject",
        "body": "Test body",
        "received_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_timezone.utc),
        "category": "General Inquiry",
        "priority": "MEDIUM",
        "ai_summary": "Test summary.",
        "ai_draft_reply": "Test draft reply.",
        "processing_status": Email.ProcessingStatus.COMPLETED,
        "status": Email.Status.NEW,
    }
    defaults.update(overrides)
    return Email.objects.create(**defaults)


# ===========================================================================
# assign_thread tests
# ===========================================================================


@pytest.mark.django_db
class TestAssignThread:
    """Test assign_thread service function."""

    def test_assign_sets_fields(self, admin_user, member_user):
        """assign_thread sets assigned_to, assigned_by, assigned_at."""
        from apps.emails.services.assignment import assign_thread

        thread = create_thread(gmail_thread_id="t_assign_1")
        result = assign_thread(thread, member_user, admin_user)

        result.refresh_from_db()
        assert result.assigned_to == member_user
        assert result.assigned_by == admin_user
        assert result.assigned_at is not None

    def test_assign_creates_activity_log(self, admin_user, member_user):
        """assign_thread creates ActivityLog with thread FK and ASSIGNED action."""
        from apps.emails.services.assignment import assign_thread

        thread = create_thread(gmail_thread_id="t_assign_2")
        assign_thread(thread, member_user, admin_user)

        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.ASSIGNED).first()
        assert log is not None
        assert log.email is None  # thread-level, no email
        assert member_user.username in log.new_value or member_user.get_full_name() in log.new_value

    def test_reassign_creates_reassigned_log(self, admin_user, member_user):
        """Reassigning creates REASSIGNED activity with old/new values."""
        from apps.emails.services.assignment import assign_thread

        other_user = User.objects.create_user(
            username="other_t", password="testpass123",
            email="other_t@vidarbhainfotech.com",
            first_name="Other", last_name="User",
        )
        thread = create_thread(gmail_thread_id="t_assign_3", assigned_to=other_user)
        assign_thread(thread, member_user, admin_user)

        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.REASSIGNED).first()
        assert log is not None
        assert "Other" in log.old_value or "other_t" in log.old_value

    @patch("apps.emails.services.assignment._send_assignment_chat")
    def test_assign_fires_chat_notification(self, mock_send_chat, admin_user, member_user):
        """assign_thread fires Chat notification (mocked)."""
        from apps.emails.services.assignment import assign_thread

        thread = create_thread(gmail_thread_id="t_assign_4")
        assign_thread(thread, member_user, admin_user)

        mock_send_chat.assert_called_once_with(thread, member_user)

    @patch("apps.emails.services.assignment.notify_assignment_email")
    def test_assign_fires_email_notification(self, mock_notify_email, admin_user, member_user):
        """assign_thread fires email notification when enabled."""
        from apps.emails.services.assignment import assign_thread
        from apps.core.models import SystemConfig

        SystemConfig.objects.update_or_create(
            key="email_notifications_enabled",
            defaults={"value": "true", "value_type": "bool"},
        )

        thread = create_thread(gmail_thread_id="t_assign_5")
        assign_thread(thread, member_user, admin_user)

        mock_notify_email.assert_called_once()


# ===========================================================================
# change_thread_status tests
# ===========================================================================


@pytest.mark.django_db
class TestChangeThreadStatus:
    """Test change_thread_status service function."""

    def test_change_status_updates_thread(self, member_user):
        """change_thread_status updates thread.status and creates ActivityLog."""
        from apps.emails.services.assignment import change_thread_status

        thread = create_thread(gmail_thread_id="t_status_1")
        change_thread_status(thread, "acknowledged", member_user)

        thread.refresh_from_db()
        assert thread.status == "acknowledged"

    def test_acknowledged_creates_acknowledged_activity(self, member_user):
        """change_thread_status with 'acknowledged' creates ACKNOWLEDGED activity."""
        from apps.emails.services.assignment import change_thread_status

        thread = create_thread(gmail_thread_id="t_status_2")
        change_thread_status(thread, "acknowledged", member_user)

        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.ACKNOWLEDGED).first()
        assert log is not None

    def test_closed_creates_closed_activity(self, member_user):
        """change_thread_status with 'closed' creates CLOSED activity."""
        from apps.emails.services.assignment import change_thread_status

        thread = create_thread(gmail_thread_id="t_status_3", status=Thread.Status.ACKNOWLEDGED)
        change_thread_status(thread, "closed", member_user)

        thread.refresh_from_db()
        assert thread.status == "closed"
        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.CLOSED).first()
        assert log is not None

    def test_invalid_status_raises_value_error(self, member_user):
        """change_thread_status raises ValueError for invalid status."""
        from apps.emails.services.assignment import change_thread_status

        thread = create_thread(gmail_thread_id="t_status_4")

        with pytest.raises(ValueError, match="Invalid status"):
            change_thread_status(thread, "bogus_status", member_user)


# ===========================================================================
# claim_thread tests
# ===========================================================================


@pytest.mark.django_db
class TestClaimThread:
    """Test claim_thread service function."""

    def test_raises_value_error_if_already_assigned(self, admin_user, member_user):
        """claim_thread raises ValueError if thread already assigned."""
        from apps.emails.services.assignment import claim_thread

        thread = create_thread(gmail_thread_id="t_claim_1", assigned_to=admin_user)

        with pytest.raises(ValueError, match="already assigned"):
            claim_thread(thread, member_user)

    def test_raises_permission_error_without_visibility(self, member_user):
        """claim_thread raises PermissionError if member lacks CategoryVisibility."""
        from apps.emails.services.assignment import claim_thread

        thread = create_thread(gmail_thread_id="t_claim_2", category="Sales Lead")

        with pytest.raises(PermissionError, match="visibility"):
            claim_thread(thread, member_user)

    def test_admin_bypasses_visibility(self, admin_user):
        """Admin can claim without CategoryVisibility."""
        from apps.emails.services.assignment import claim_thread

        thread = create_thread(gmail_thread_id="t_claim_3", category="Sales Lead")

        result = claim_thread(thread, admin_user)
        result.refresh_from_db()
        assert result.assigned_to == admin_user

    def test_creates_claimed_activity_log(self, member_user):
        """claim_thread creates CLAIMED activity log."""
        from apps.emails.services.assignment import claim_thread

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        thread = create_thread(gmail_thread_id="t_claim_4", category="Sales Lead")

        claim_thread(thread, member_user)

        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.CLAIMED).first()
        assert log is not None


# ===========================================================================
# update_thread_preview tests
# ===========================================================================


@pytest.mark.django_db
class TestUpdateThreadPreview:
    """Test update_thread_preview service function."""

    def test_sets_latest_sender_fields(self, admin_user):
        """update_thread_preview sets last_message_at, last_sender, last_sender_address from latest email."""
        from apps.emails.services.assignment import update_thread_preview

        thread = create_thread(gmail_thread_id="t_preview_1")
        _create_email_on_thread(
            thread,
            message_id="msg_preview_1a",
            from_name="Old Sender",
            from_address="old@example.com",
            received_at=datetime(2026, 3, 8, 10, 0, 0, tzinfo=dt_timezone.utc),
        )
        _create_email_on_thread(
            thread,
            message_id="msg_preview_1b",
            from_name="Latest Sender",
            from_address="latest@example.com",
            received_at=datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_timezone.utc),
        )

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.last_sender == "Latest Sender"
        assert thread.last_sender_address == "latest@example.com"
        assert thread.last_message_at == datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_timezone.utc)

    def test_sets_subject_from_earliest_email(self, admin_user):
        """update_thread_preview sets subject from earliest email in thread."""
        from apps.emails.services.assignment import update_thread_preview

        thread = create_thread(gmail_thread_id="t_preview_2", subject="")
        _create_email_on_thread(
            thread,
            message_id="msg_preview_2a",
            subject="Original Subject",
            received_at=datetime(2026, 3, 8, 10, 0, 0, tzinfo=dt_timezone.utc),
        )
        _create_email_on_thread(
            thread,
            message_id="msg_preview_2b",
            subject="Re: Original Subject",
            received_at=datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_timezone.utc),
        )

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.subject == "Original Subject"

    def test_updates_triage_from_latest_completed_email(self, admin_user):
        """update_thread_preview updates category/priority/ai_summary/ai_draft_reply from latest triaged email."""
        from apps.emails.services.assignment import update_thread_preview

        thread = create_thread(gmail_thread_id="t_preview_3")
        _create_email_on_thread(
            thread,
            message_id="msg_preview_3a",
            category="Old Category",
            priority="LOW",
            ai_summary="Old summary",
            ai_draft_reply="Old reply",
            received_at=datetime(2026, 3, 8, 10, 0, 0, tzinfo=dt_timezone.utc),
            processing_status=Email.ProcessingStatus.COMPLETED,
        )
        _create_email_on_thread(
            thread,
            message_id="msg_preview_3b",
            category="New Category",
            priority="HIGH",
            ai_summary="New summary",
            ai_draft_reply="New reply",
            received_at=datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_timezone.utc),
            processing_status=Email.ProcessingStatus.COMPLETED,
        )

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.category == "New Category"
        assert thread.priority == "HIGH"
        assert thread.ai_summary == "New summary"
        assert thread.ai_draft_reply == "New reply"

    def test_handles_thread_with_no_emails(self, admin_user):
        """update_thread_preview handles thread with no emails gracefully (no-op)."""
        from apps.emails.services.assignment import update_thread_preview

        thread = create_thread(gmail_thread_id="t_preview_4")

        result = update_thread_preview(thread)
        assert result is None
