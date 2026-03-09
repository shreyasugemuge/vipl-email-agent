"""Tests for Email and AttachmentMetadata models."""

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import AttachmentMetadata, Email


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
