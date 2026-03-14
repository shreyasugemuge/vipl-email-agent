"""Tests for email assignment service, status changes, and notifications."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import Email, ActivityLog


def _create_email(db, **overrides):
    """Helper to create a completed Email record with sensible defaults."""
    defaults = {
        "message_id": f"msg_{id(overrides)}_{overrides.get('subject', 'test')}",
        "from_address": "sender@example.com",
        "from_name": "Test Sender",
        "to_inbox": "info@vidarbhainfotech.com",
        "subject": "Test Subject",
        "body": "Test body",
        "received_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        "category": "General Inquiry",
        "priority": "MEDIUM",
        "ai_summary": "This is a test email summary.",
        "processing_status": Email.ProcessingStatus.COMPLETED,
        "status": Email.Status.NEW,
    }
    defaults.update(overrides)
    return Email.objects.create(**defaults)


# ===========================================================================
# Assignment service tests
# ===========================================================================


@pytest.mark.django_db
class TestAssignEmail:
    """Test assign_email service function."""

    def test_assign_sets_fields(self, admin_user, member_user):
        """Test 1: assign_email sets assigned_to, assigned_by, assigned_at."""
        from apps.emails.services.assignment import assign_email

        email = _create_email(None, message_id="msg_assign_1")
        result = assign_email(email, member_user, admin_user)

        result.refresh_from_db()
        assert result.assigned_to == member_user
        assert result.assigned_by == admin_user
        assert result.assigned_at is not None

    def test_assign_creates_activity_log(self, admin_user, member_user):
        """Test 2: assign_email creates ActivityLog with action=ASSIGNED."""
        from apps.emails.services.assignment import assign_email

        email = _create_email(None, message_id="msg_assign_2")
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
        email = _create_email(None, message_id="msg_assign_3", assigned_to=other_user)
        assign_email(email, member_user, admin_user)

        log = ActivityLog.objects.filter(email=email, action=ActivityLog.Action.REASSIGNED).first()
        assert log is not None
        assert "Other" in log.old_value or "other" in log.old_value
        assert member_user.username in log.new_value or member_user.get_full_name() in log.new_value

    def test_assign_with_note(self, admin_user, member_user):
        """Test 4: assign_email with note stores note in ActivityLog.detail."""
        from apps.emails.services.assignment import assign_email

        email = _create_email(None, message_id="msg_assign_4")
        assign_email(email, member_user, admin_user, note="Please handle urgently")

        log = ActivityLog.objects.filter(email=email).first()
        assert log is not None
        assert "Please handle urgently" in log.detail

    @patch("apps.emails.services.assignment._send_assignment_chat")
    def test_assign_calls_chat_notifier(self, mock_send_chat, admin_user, member_user):
        """Test 5: assign_email calls _send_assignment_chat."""
        from apps.emails.services.assignment import assign_email

        email = _create_email(None, message_id="msg_assign_5")
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

        email = _create_email(None, message_id="msg_assign_6")
        assign_email(email, member_user, admin_user)

        mock_notify_email.assert_called_once()


@pytest.mark.django_db
class TestChangeStatus:
    """Test change_status service function."""

    def test_change_status_updates_email(self, admin_user, member_user):
        """Test 7: change_status updates Email.status and creates ActivityLog."""
        from apps.emails.services.assignment import change_status

        email = _create_email(None, message_id="msg_status_7", assigned_to=member_user)
        change_status(email, "acknowledged", member_user)

        email.refresh_from_db()
        assert email.status == "acknowledged"
        log = ActivityLog.objects.filter(email=email).first()
        assert log is not None
        assert log.action == ActivityLog.Action.ACKNOWLEDGED

    def test_acknowledge_status(self, member_user):
        """Test 8: change_status with ACKNOWLEDGED sets correct status."""
        from apps.emails.services.assignment import change_status

        email = _create_email(None, message_id="msg_status_8", assigned_to=member_user)
        change_status(email, "acknowledged", member_user)

        email.refresh_from_db()
        assert email.status == "acknowledged"

    def test_close_status(self, member_user):
        """Test 9: change_status with CLOSED sets correct status."""
        from apps.emails.services.assignment import change_status

        email = _create_email(
            None, message_id="msg_status_9",
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

        email = _create_email(None, message_id="msg_chat_10", subject="Test assignment chat")

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

        email = _create_email(None, message_id="msg_chat_11")

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

        email = _create_email(
            None, message_id="msg_email_12",
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
# View-level tests
# ===========================================================================


@pytest.fixture
def admin_client(admin_user):
    """Authenticated client logged in as admin."""
    c = Client()
    c.login(username="admin", password="testpass123")
    return c


@pytest.fixture
def member_client(member_user):
    """Authenticated client logged in as member."""
    c = Client()
    c.login(username="member", password="testpass123")
    return c


@pytest.mark.django_db
class TestAssignEmailView:
    """Test assign_email_view endpoint."""

    def test_non_admin_returns_403(self, member_client, member_user, admin_user):
        """View Test 1: Non-admin POST to assign returns 403."""
        email = _create_email(None, message_id="msg_v_assign_1")
        response = member_client.post(
            reverse("emails:assign_email", args=[email.pk]),
            {"assignee_id": admin_user.pk},
        )
        assert response.status_code == 403

    def test_admin_assigns_successfully(self, admin_client, admin_user, member_user):
        """View Test 2: Admin POST to assign returns 200 and updates assignee."""
        email = _create_email(None, message_id="msg_v_assign_2")
        response = admin_client.post(
            reverse("emails:assign_email", args=[email.pk]),
            {"assignee_id": member_user.pk},
        )
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.assigned_to == member_user


@pytest.mark.django_db
class TestChangeStatusView:
    """Test change_status_view endpoint."""

    def test_member_cannot_change_others_email(self, member_client, member_user, admin_user):
        """View Test 3: Member cannot change status on email not assigned to them."""
        email = _create_email(None, message_id="msg_v_status_3", assigned_to=admin_user)
        response = member_client.post(
            reverse("emails:change_status", args=[email.pk]),
            {"new_status": "acknowledged"},
        )
        assert response.status_code == 403

    def test_member_acknowledges_own_email(self, member_client, member_user):
        """View Test 4: Member can acknowledge their own assigned email."""
        email = _create_email(None, message_id="msg_v_status_4", assigned_to=member_user)
        response = member_client.post(
            reverse("emails:change_status", args=[email.pk]),
            {"new_status": "acknowledged"},
        )
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.status == "acknowledged"

    def test_member_closes_own_email(self, member_client, member_user):
        """View Test 5: Member can close their own assigned email."""
        email = _create_email(
            None, message_id="msg_v_status_5",
            assigned_to=member_user,
            status=Email.Status.ACKNOWLEDGED,
        )
        response = member_client.post(
            reverse("emails:change_status", args=[email.pk]),
            {"new_status": "closed"},
        )
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.status == "closed"

    def test_admin_changes_any_email_status(self, admin_client, admin_user, member_user):
        """View Test 6: Admin can change status on any email."""
        email = _create_email(None, message_id="msg_v_status_6", assigned_to=member_user)
        response = admin_client.post(
            reverse("emails:change_status", args=[email.pk]),
            {"new_status": "acknowledged"},
        )
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.status == "acknowledged"


@pytest.mark.django_db
class TestEmailDetailView:
    """Test email_detail view."""

    def test_sanitizes_body_html(self, admin_client, admin_user):
        """View Test 7: body_html with script tags is sanitized."""
        email = _create_email(
            None, message_id="msg_v_detail_7",
            body_html="<p>Hello</p><script>alert('xss')</script><strong>safe</strong>",
        )
        response = admin_client.get(
            reverse("emails:email_detail", args=[email.pk]),
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "<script>" not in content
        assert "<p>Hello</p>" in content
        assert "<strong>safe</strong>" in content

    def test_returns_detail_with_activity_log(self, admin_client, admin_user, member_user):
        """View Test 8: email_detail returns email body, attachments, activity log."""
        email = _create_email(
            None, message_id="msg_v_detail_8",
            body="Detailed test body",
            subject="Detail test subject",
        )
        # Create an activity log entry
        ActivityLog.objects.create(
            email=email,
            user=admin_user,
            action=ActivityLog.Action.ASSIGNED,
            new_value=member_user.username,
        )
        response = admin_client.get(
            reverse("emails:email_detail", args=[email.pk]),
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "Detail test subject" in content
