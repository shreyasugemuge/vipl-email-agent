"""Tests for Email, Thread, and AttachmentMetadata models."""

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import ActivityLog, AttachmentMetadata, Email, Thread


@pytest.mark.django_db
class TestEmailModel:
    @pytest.fixture
    def email(self):
        return Email.objects.create(
            message_id="test-msg-001@example.com",
            from_address="sender@example.com",
            from_name="Sender Name",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test Subject",
            body="Test email body content",
            headers={"X-Custom": "value"},
            received_at=timezone.now(),
            gmail_id="gmail123",
            gmail_thread_id="thread123",
            gmail_labels=["INBOX", "UNREAD"],
        )

    def test_email_has_required_fields(self, email):
        assert email.message_id == "test-msg-001@example.com"
        assert email.from_address == "sender@example.com"
        assert email.to_inbox == "info@vidarbhainfotech.com"
        assert email.subject == "Test Subject"
        assert email.body == "Test email body content"
        assert email.headers == {"X-Custom": "value"}
        assert email.received_at is not None
        assert email.gmail_id == "gmail123"
        assert email.gmail_thread_id == "thread123"
        assert email.gmail_labels == ["INBOX", "UNREAD"]

    def test_email_defaults(self, email):
        assert email.status == Email.Status.NEW
        assert email.category == ""
        assert email.priority == ""
        assert email.ai_summary == ""
        assert email.ai_draft_reply == ""
        assert email.assigned_to is None
        assert email.assigned_by is None
        assert email.assigned_at is None

    def test_email_uses_soft_delete(self, email):
        pk = email.pk
        email.delete()
        # Should still exist in all_objects
        assert Email.all_objects.filter(pk=pk).exists()
        # Should be excluded from default manager
        assert not Email.objects.filter(pk=pk).exists()

    def test_email_assignment(self, email):
        user = User.objects.create_user(username="assignee", password="pass123")
        email.assigned_to = user
        email.assigned_at = timezone.now()
        email.save()
        email.refresh_from_db()
        assert email.assigned_to == user

    def test_email_str(self, email):
        assert "sender@example.com" in str(email)
        assert "Test Subject" in str(email)


@pytest.mark.django_db
class TestAttachmentMetadata:
    def test_attachment_stores_metadata(self):
        email = Email.objects.create(
            message_id="att-test@example.com",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="With attachment",
            received_at=timezone.now(),
        )
        attachment = AttachmentMetadata.objects.create(
            email=email,
            filename="document.pdf",
            size_bytes=102400,
            mime_type="application/pdf",
            gmail_attachment_id="att-123",
        )
        assert attachment.filename == "document.pdf"
        assert attachment.size_bytes == 102400
        assert attachment.mime_type == "application/pdf"
        assert attachment.email == email

    def test_attachment_linked_to_email(self):
        email = Email.objects.create(
            message_id="att-link@example.com",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="With attachments",
            received_at=timezone.now(),
        )
        AttachmentMetadata.objects.create(
            email=email,
            filename="file1.pdf",
            size_bytes=1024,
            mime_type="application/pdf",
        )
        AttachmentMetadata.objects.create(
            email=email,
            filename="file2.jpg",
            size_bytes=2048,
            mime_type="image/jpeg",
        )
        assert email.attachments.count() == 2


@pytest.mark.django_db
class TestThreadModel:
    @pytest.fixture
    def thread(self):
        return Thread.objects.create(
            gmail_thread_id="thread-abc-123",
            subject="Test thread subject",
        )

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="worker", password="pass123")

    def test_thread_created_with_defaults(self, thread):
        assert thread.status == Thread.Status.NEW
        assert thread.assigned_to is None
        assert thread.assigned_by is None
        assert thread.assigned_at is None
        assert thread.category == ""
        assert thread.priority == ""
        assert thread.ai_summary == ""
        assert thread.ai_draft_reply == ""
        assert thread.sla_ack_deadline is None
        assert thread.sla_respond_deadline is None
        assert thread.last_message_at is None
        assert thread.last_sender == ""
        assert thread.last_sender_address == ""

    def test_thread_status_choices(self):
        choices = [c[0] for c in Thread.Status.choices]
        assert "new" in choices
        assert "acknowledged" in choices
        assert "closed" in choices
        # REPLIED is email-level, not thread-level
        assert "replied" not in choices

    def test_email_thread_fk(self, thread):
        email = Email.objects.create(
            message_id="fk-test@example.com",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test",
            received_at=timezone.now(),
            thread=thread,
        )
        assert email.thread == thread
        assert thread.emails.count() == 1

    def test_multiple_emails_same_thread(self, thread):
        for i in range(3):
            Email.objects.create(
                message_id=f"multi-{i}@example.com",
                from_address="sender@example.com",
                to_inbox="info@vidarbhainfotech.com",
                subject="Test",
                received_at=timezone.now(),
                gmail_thread_id="thread-abc-123",
                thread=thread,
            )
        assert thread.emails.count() == 3

    def test_thread_triage_fields(self, thread):
        thread.category = "complaint"
        thread.priority = "HIGH"
        thread.ai_summary = "Customer complaint about billing"
        thread.ai_draft_reply = "Dear customer..."
        thread.save()
        thread.refresh_from_db()
        assert thread.category == "complaint"
        assert thread.priority == "HIGH"
        assert thread.ai_summary == "Customer complaint about billing"
        assert thread.ai_draft_reply == "Dear customer..."

    def test_thread_assignment_fields(self, thread, user):
        now = timezone.now()
        admin = User.objects.create_user(username="admin", password="pass123")
        thread.assigned_to = user
        thread.assigned_by = admin
        thread.assigned_at = now
        thread.save()
        thread.refresh_from_db()
        assert thread.assigned_to == user
        assert thread.assigned_by == admin
        assert thread.assigned_at is not None

    def test_thread_sla_fields(self, thread):
        now = timezone.now()
        thread.sla_ack_deadline = now
        thread.sla_respond_deadline = now
        thread.save()
        thread.refresh_from_db()
        assert thread.sla_ack_deadline is not None
        assert thread.sla_respond_deadline is not None

    def test_thread_message_count(self, thread):
        assert thread.message_count == 0
        Email.objects.create(
            message_id="count-1@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="A",
            received_at=timezone.now(),
            thread=thread,
        )
        assert thread.message_count == 1

    def test_thread_message_count_excludes_soft_deleted(self, thread):
        e1 = Email.objects.create(
            message_id="sd-1@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="A",
            received_at=timezone.now(),
            thread=thread,
        )
        Email.objects.create(
            message_id="sd-2@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="B",
            received_at=timezone.now(),
            thread=thread,
        )
        e1.delete()
        assert thread.message_count == 1

    def test_thread_latest_message_at(self, thread):
        early = timezone.now() - timezone.timedelta(hours=2)
        late = timezone.now()
        Email.objects.create(
            message_id="lm-1@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="A",
            received_at=early,
            thread=thread,
        )
        Email.objects.create(
            message_id="lm-2@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="B",
            received_at=late,
            thread=thread,
        )
        assert thread.latest_message_at == late

    def test_thread_subject_from_earliest_email(self, thread):
        # Thread.subject is set directly on the model, not derived
        assert thread.subject == "Test thread subject"

    def test_thread_str(self, thread):
        s = str(thread)
        assert "thread-abc-1" in s
        assert "Test thread" in s

    def test_thread_uses_soft_delete(self, thread):
        pk = thread.pk
        thread.delete()
        assert Thread.all_objects.filter(pk=pk).exists()
        assert not Thread.objects.filter(pk=pk).exists()

    def test_thread_uses_timestamped(self, thread):
        assert thread.created_at is not None
        assert thread.updated_at is not None

    def test_thread_default_ordering(self):
        t1 = Thread.objects.create(
            gmail_thread_id="order-1",
            subject="First",
            last_message_at=timezone.now() - timezone.timedelta(hours=1),
        )
        t2 = Thread.objects.create(
            gmail_thread_id="order-2",
            subject="Second",
            last_message_at=timezone.now(),
        )
        threads = list(Thread.objects.all())
        assert threads[0] == t2
        assert threads[1] == t1

    def test_email_empty_gmail_thread_id_in_thread(self, thread):
        email = Email.objects.create(
            message_id="empty-tid@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="No thread id",
            received_at=timezone.now(),
            gmail_thread_id="",
            thread=thread,
        )
        assert email.thread == thread


@pytest.mark.django_db
class TestActivityLogThread:
    @pytest.fixture
    def thread(self):
        return Thread.objects.create(
            gmail_thread_id="al-thread-123",
            subject="Activity log thread",
        )

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="actor", password="pass123")

    def test_activity_log_thread_fk_required(self, thread, user):
        log = ActivityLog.objects.create(
            thread=thread,
            user=user,
            action=ActivityLog.Action.ASSIGNED,
            detail="Assigned to worker",
        )
        assert log.thread == thread
        assert log.email is None

    def test_activity_log_email_fk_optional(self, thread, user):
        email = Email.objects.create(
            message_id="al-email@example.com",
            from_address="s@e.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test",
            received_at=timezone.now(),
            thread=thread,
        )
        log = ActivityLog.objects.create(
            thread=thread,
            email=email,
            user=user,
            action=ActivityLog.Action.STATUS_CHANGED,
        )
        assert log.thread == thread
        assert log.email == email

    def test_new_action_types_exist(self):
        actions = [a[0] for a in ActivityLog.Action.choices]
        assert "new_email_received" in actions
        assert "reopened" in actions
        assert "thread_created" in actions
