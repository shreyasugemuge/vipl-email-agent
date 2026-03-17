"""Tests for email assignment service, status changes, notifications, and claiming."""

import pytest
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, MagicMock

from apps.accounts.models import User
from apps.emails.models import ActivityLog, CategoryVisibility, Email, Thread
from conftest import create_email, create_thread


# ===========================================================================
# Assignment service tests
# ===========================================================================


@pytest.mark.django_db
class TestAssignEmail:
    """Test assign_email service function."""

    def test_assign_sets_fields(self, admin_user, member_user):
        """Test 1: assign_email sets assigned_to, assigned_by, assigned_at."""
        from apps.emails.services.assignment import assign_email

        email = create_email(message_id="msg_assign_1")
        result = assign_email(email, member_user, admin_user)

        result.refresh_from_db()
        assert result.assigned_to == member_user
        assert result.assigned_by == admin_user
        assert result.assigned_at is not None

    def test_assign_creates_activity_log(self, admin_user, member_user):
        """Test 2: assign_email creates ActivityLog with action=ASSIGNED."""
        from apps.emails.services.assignment import assign_email

        email = create_email(message_id="msg_assign_2")
        assign_email(email, member_user, admin_user)

        log = ActivityLog.objects.filter(email=email).first()
        assert log is not None
        assert log.action == ActivityLog.Action.ASSIGNED
        assert member_user.get_full_name() in log.new_value or member_user.username in log.new_value

    def test_reassign_creates_reassigned_log(self, admin_user, member_user):
        """Test 3: reassign creates ActivityLog with REASSIGNED action and old/new values."""
        from apps.emails.services.assignment import assign_email

        other_user = User.objects.create_user(
            username="other", password="testpass123",
            email="other@vidarbhainfotech.com",
            first_name="Other", last_name="User",
        )
        email = create_email(message_id="msg_assign_3", assigned_to=other_user)
        assign_email(email, member_user, admin_user)

        log = ActivityLog.objects.filter(email=email, action=ActivityLog.Action.REASSIGNED).first()
        assert log is not None
        assert "Other" in log.old_value or "other" in log.old_value
        assert member_user.username in log.new_value or member_user.get_full_name() in log.new_value

    def test_assign_with_note(self, admin_user, member_user):
        """Test 4: assign_email with note stores note in ActivityLog.detail."""
        from apps.emails.services.assignment import assign_email

        email = create_email(message_id="msg_assign_4")
        assign_email(email, member_user, admin_user, note="Please handle urgently")

        log = ActivityLog.objects.filter(email=email).first()
        assert log is not None
        assert "Please handle urgently" in log.detail

    @patch("apps.emails.services.assignment._send_assignment_chat")
    def test_assign_calls_chat_notifier(self, mock_send_chat, admin_user, member_user):
        """Test 5: assign_email calls _send_assignment_chat."""
        from apps.emails.services.assignment import assign_email

        email = create_email(message_id="msg_assign_5")
        assign_email(email, member_user, admin_user)

        mock_send_chat.assert_called_once_with(email, member_user)

    @patch("apps.emails.services.assignment.notify_assignment_email")
    def test_assign_calls_email_notification(self, mock_notify_email, admin_user, member_user):
        """Test 6: assign_email calls notify_assignment_email when enabled."""
        from apps.emails.services.assignment import assign_email
        from apps.core.models import SystemConfig

        # Enable email notifications for this test
        SystemConfig.objects.update_or_create(
            key="email_notifications_enabled",
            defaults={"value": "true", "value_type": "bool"},
        )

        email = create_email(message_id="msg_assign_6")
        assign_email(email, member_user, admin_user)

        mock_notify_email.assert_called_once()


@pytest.mark.django_db
class TestChangeStatus:
    """Test change_status service function."""

    def test_change_status_updates_email(self, admin_user, member_user):
        """Test 7: change_status updates Email.status and creates ActivityLog."""
        from apps.emails.services.assignment import change_status

        email = create_email(message_id="msg_status_7", assigned_to=member_user)
        change_status(email, "acknowledged", member_user)

        email.refresh_from_db()
        assert email.status == "acknowledged"
        log = ActivityLog.objects.filter(email=email).first()
        assert log is not None
        assert log.action == ActivityLog.Action.ACKNOWLEDGED

    def test_acknowledge_status(self, member_user):
        """Test 8: change_status with ACKNOWLEDGED sets correct status."""
        from apps.emails.services.assignment import change_status

        email = create_email(message_id="msg_status_8", assigned_to=member_user)
        change_status(email, "acknowledged", member_user)

        email.refresh_from_db()
        assert email.status == "acknowledged"

    def test_close_status(self, member_user):
        """Test 9: change_status with CLOSED sets correct status."""
        from apps.emails.services.assignment import change_status

        email = create_email(
            message_id="msg_status_9",
            assigned_to=member_user,
            status=Email.Status.ACKNOWLEDGED,
        )
        change_status(email, "closed", member_user)

        email.refresh_from_db()
        assert email.status == "closed"
        log = ActivityLog.objects.filter(email=email, action=ActivityLog.Action.CLOSED).first()
        assert log is not None


@pytest.mark.django_db
class TestChatNotifierAssignment:
    """Test ChatNotifier.notify_assignment method."""

    def test_notify_assignment_payload(self, admin_user, member_user):
        """Test 10: notify_assignment sends Cards v2 payload with correct fields."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        email = create_email(message_id="msg_chat_10", subject="Test assignment chat")

        with patch.object(notifier, "_is_quiet_hours", return_value=False):
            with patch.object(notifier, "_post", return_value=True) as mock_post:
                result = notifier.notify_assignment(email, member_user)

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        assert "cardsV2" in payload
        card = payload["cardsV2"][0]["card"]
        assert "Test assignment chat" in card["header"]["title"]

    def test_notify_assignment_quiet_hours(self, member_user):
        """Test 11: notify_assignment respects quiet hours."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        email = create_email(message_id="msg_chat_11")

        with patch.object(notifier, "_is_quiet_hours", return_value=True):
            with patch.object(notifier, "_post") as mock_post:
                result = notifier.notify_assignment(email, member_user)

        assert result is False
        mock_post.assert_not_called()


@pytest.mark.django_db
class TestNotifyAssignmentEmail:
    """Test notify_assignment_email function."""

    @patch("apps.emails.services.assignment.send_mail")
    def test_sends_email_to_assignee(self, mock_send_mail, admin_user, member_user):
        """Test 12: notify_assignment_email sends email with correct details."""
        from apps.emails.services.assignment import notify_assignment_email

        email = create_email(
            message_id="msg_email_12",
            subject="Important inquiry",
            ai_summary="Customer asking about pricing",
        )

        result = notify_assignment_email(email, member_user)

        assert result is True
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert "Important inquiry" in call_args[1].get("subject", call_args[0][0] if call_args[0] else "")
        # Check recipient
        recipients = call_args[1].get("recipient_list", call_args[0][3] if len(call_args[0]) > 3 else [])
        assert member_user.email in recipients


# ===========================================================================
# Claim email tests
# ===========================================================================


@pytest.mark.django_db
class TestClaimEmail:
    """Test claim_email service function."""

    def test_successful_claim(self, member_user):
        """Claim sets assignee and creates activity log."""
        from apps.emails.services.assignment import claim_email

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        email = create_email(category="Sales Lead", message_id="msg_claim_1")

        result = claim_email(email, member_user)

        result.refresh_from_db()
        assert result.assigned_to == member_user
        log = ActivityLog.objects.filter(email=email, action=ActivityLog.Action.CLAIMED).first()
        assert log is not None

    def test_raises_value_error_when_already_assigned(self, admin_user, member_user):
        """Raises ValueError if email already assigned."""
        from apps.emails.services.assignment import claim_email

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        email = create_email(category="Sales Lead", message_id="msg_claim_2", assigned_to=admin_user)

        with pytest.raises(ValueError, match="already assigned"):
            claim_email(email, member_user)

    def test_raises_permission_error_without_visibility(self, member_user):
        """Raises PermissionError if member lacks category visibility."""
        from apps.emails.services.assignment import claim_email

        email = create_email(category="Sales Lead", message_id="msg_claim_3")

        with pytest.raises(PermissionError, match="visibility"):
            claim_email(email, member_user)

    def test_admin_bypasses_visibility(self, admin_user):
        """Admin can claim without CategoryVisibility."""
        from apps.emails.services.assignment import claim_email

        email = create_email(category="Sales Lead", message_id="msg_claim_4")

        result = claim_email(email, admin_user)
        result.refresh_from_db()
        assert result.assigned_to == admin_user

    def test_claimed_action_in_log(self, member_user):
        """ActivityLog shows CLAIMED action (not ASSIGNED)."""
        from apps.emails.services.assignment import claim_email

        CategoryVisibility.objects.create(user=member_user, category="Sales Lead")
        email = create_email(category="Sales Lead", message_id="msg_claim_5")

        claim_email(email, member_user)

        logs = ActivityLog.objects.filter(email=email)
        actions = [log.action for log in logs]
        assert ActivityLog.Action.CLAIMED in actions


# ===========================================================================
# Thread assignment tests
# ===========================================================================


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


