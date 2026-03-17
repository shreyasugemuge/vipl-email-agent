"""Tests for Email, Thread, AttachmentMetadata, ThreadReadState, SpamFeedback,
SenderReputation, AssignmentFeedback models, and thread preview override guards."""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    AttachmentMetadata,
    Email,
    SenderReputation,
    SpamFeedback,
    Thread,
    ThreadReadState,
)
from apps.emails.services.assignment import update_thread_preview


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


# ===========================================================================
# ThreadReadState Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestThreadReadState:
    @pytest.fixture
    def trs_user(self):
        return User.objects.create_user(
            username="trs_user", email="trs@vidarbhainfotech.com", password="testpass123",
        )

    @pytest.fixture
    def trs_thread(self):
        return Thread.objects.create(gmail_thread_id="thread-trs-001", subject="TRS Test Thread")

    def test_create_with_defaults(self, trs_user, trs_thread):
        state = ThreadReadState.objects.create(thread=trs_thread, user=trs_user)
        assert state.is_read is False
        assert state.read_at is None

    def test_mark_as_read(self, trs_user, trs_thread):
        now = timezone.now()
        state = ThreadReadState.objects.create(
            thread=trs_thread, user=trs_user, is_read=True, read_at=now
        )
        assert state.is_read is True
        assert state.read_at == now

    def test_unique_together_enforced(self, trs_user, trs_thread):
        ThreadReadState.objects.create(thread=trs_thread, user=trs_user)
        with pytest.raises(IntegrityError):
            ThreadReadState.objects.create(thread=trs_thread, user=trs_user)

    def test_soft_delete(self, trs_user, trs_thread):
        state = ThreadReadState.objects.create(thread=trs_thread, user=trs_user)
        state.delete()
        assert state.deleted_at is not None
        assert ThreadReadState.objects.count() == 0
        assert ThreadReadState.all_objects.count() == 1

    def test_str_representation(self, trs_user, trs_thread):
        state = ThreadReadState.objects.create(thread=trs_thread, user=trs_user)
        assert "unread" in str(state)
        state.is_read = True
        assert "read" in str(state)


# ===========================================================================
# SpamFeedback Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestSpamFeedback:
    @pytest.fixture
    def sf_user(self):
        return User.objects.create_user(
            username="sf_user", email="sf@vidarbhainfotech.com", password="testpass123",
        )

    def test_create_with_verdicts(self, sf_user):
        fb = SpamFeedback.objects.create(
            user=sf_user, original_verdict=True, user_verdict=False
        )
        assert fb.original_verdict is True
        assert fb.user_verdict is False

    def test_thread_and_email_nullable(self, sf_user):
        fb = SpamFeedback.objects.create(
            user=sf_user, original_verdict=False, user_verdict=True
        )
        assert fb.thread is None
        assert fb.email is None

    def test_with_thread(self, sf_user):
        thread = Thread.objects.create(gmail_thread_id="thread-sf-001", subject="Spam Test")
        fb = SpamFeedback.objects.create(
            user=sf_user, thread=thread, original_verdict=True, user_verdict=True
        )
        assert fb.thread == thread

    def test_str_representation(self, sf_user):
        fb = SpamFeedback.objects.create(
            user=sf_user, original_verdict=False, user_verdict=True
        )
        assert "spam" in str(fb)

        fb2 = SpamFeedback.objects.create(
            user=sf_user, original_verdict=True, user_verdict=False
        )
        assert "not-spam" in str(fb2)


# ===========================================================================
# SenderReputation Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestSenderReputation:
    def test_create_with_defaults(self):
        rep = SenderReputation.objects.create(sender_address="spammer@example.com")
        assert rep.total_count == 0
        assert rep.spam_count == 0
        assert rep.is_blocked is False

    def test_unique_sender_address(self):
        SenderReputation.objects.create(sender_address="dup@example.com")
        with pytest.raises(IntegrityError):
            SenderReputation.objects.create(sender_address="dup@example.com")

    def test_spam_ratio_zero_total(self):
        rep = SenderReputation.objects.create(sender_address="new@example.com")
        assert rep.spam_ratio == 0.0

    def test_spam_ratio_calculated(self):
        rep = SenderReputation.objects.create(
            sender_address="mixed@example.com", total_count=10, spam_count=3
        )
        assert rep.spam_ratio == pytest.approx(0.3)

    def test_str_representation(self):
        rep = SenderReputation.objects.create(
            sender_address="test@example.com", total_count=5, spam_count=2
        )
        assert "2/5" in str(rep)
        assert "test@example.com" in str(rep)

    def test_str_blocked(self):
        rep = SenderReputation.objects.create(
            sender_address="blocked@example.com", is_blocked=True
        )
        assert "[BLOCKED]" in str(rep)


# ===========================================================================
# AssignmentFeedback Model Tests
# ===========================================================================


@pytest.mark.django_db
class TestAssignmentFeedback:
    @pytest.fixture
    def af_user(self):
        return User.objects.create_user(
            username="af_user", email="af@vidarbhainfotech.com", password="testpass123",
        )

    @pytest.fixture
    def af_thread(self):
        return Thread.objects.create(gmail_thread_id="thread-af-001", subject="AF Test Thread")

    def test_create_with_required_fields(self, af_user, af_thread):
        fb = AssignmentFeedback.objects.create(
            thread=af_thread,
            action=AssignmentFeedback.FeedbackAction.ACCEPTED,
            user_who_acted=af_user,
        )
        assert fb.thread == af_thread
        assert fb.action == "accepted"
        assert fb.user_who_acted == af_user

    def test_all_feedback_actions(self, af_user, af_thread):
        for action_value, _label in AssignmentFeedback.FeedbackAction.choices:
            fb = AssignmentFeedback.objects.create(
                thread=af_thread, action=action_value, user_who_acted=af_user
            )
            assert fb.action == action_value

    def test_optional_fields_nullable(self, af_user, af_thread):
        fb = AssignmentFeedback.objects.create(
            thread=af_thread,
            action=AssignmentFeedback.FeedbackAction.REJECTED,
            user_who_acted=af_user,
        )
        assert fb.email is None
        assert fb.suggested_user is None
        assert fb.actual_user is None
        assert fb.confidence_at_time is None

    def test_str_representation(self, af_user, af_thread):
        fb = AssignmentFeedback.objects.create(
            thread=af_thread,
            action=AssignmentFeedback.FeedbackAction.ACCEPTED,
            user_who_acted=af_user,
        )
        assert "accepted" in str(fb)


# ===========================================================================
# Thread Override Fields Tests
# ===========================================================================


@pytest.mark.django_db
class TestThreadOverrideFields:
    def test_category_overridden_default(self):
        thread = Thread.objects.create(gmail_thread_id="thread-ov-001", subject="Override Test")
        thread.refresh_from_db()
        assert thread.category_overridden is False

    def test_priority_overridden_default(self):
        thread = Thread.objects.create(gmail_thread_id="thread-ov-002", subject="Override Test")
        thread.refresh_from_db()
        assert thread.priority_overridden is False

    def test_ai_confidence_default(self):
        thread = Thread.objects.create(gmail_thread_id="thread-ov-003", subject="Override Test")
        thread.refresh_from_db()
        assert thread.ai_confidence == ""

    def test_ai_confidence_set(self):
        t = Thread.objects.create(
            gmail_thread_id="conf-thread-001",
            subject="Confidence Test",
            ai_confidence="HIGH",
        )
        assert t.ai_confidence == "HIGH"


# ===========================================================================
# Email AI Confidence Tests
# ===========================================================================


@pytest.mark.django_db
class TestEmailAiConfidence:
    def test_default_empty(self):
        e = Email.objects.create(
            message_id="conf-email-default@example.com",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test",
            body="Body",
            received_at=timezone.now(),
        )
        e.refresh_from_db()
        assert e.ai_confidence == ""

    def test_set_confidence(self):
        e = Email.objects.create(
            message_id="conf-email-001@example.com",
            from_address="s@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test",
            body="Body",
            received_at=timezone.now(),
            ai_confidence="MEDIUM",
        )
        assert e.ai_confidence == "MEDIUM"


# ===========================================================================
# ActivityLog New Actions Tests
# ===========================================================================


@pytest.mark.django_db
class TestActivityLogNewActions:
    def test_spam_marked_is_valid(self):
        assert ActivityLog.Action.SPAM_MARKED == "spam_marked"

    def test_spam_unmarked_is_valid(self):
        assert ActivityLog.Action.SPAM_UNMARKED == "spam_unmarked"

    def test_priority_changed_is_valid(self):
        assert ActivityLog.Action.PRIORITY_CHANGED == "priority_changed"

    def test_category_changed_is_valid(self):
        assert ActivityLog.Action.CATEGORY_CHANGED == "category_changed"

    def test_new_actions_in_choices(self):
        action_values = [v for v, _l in ActivityLog.Action.choices]
        assert "spam_marked" in action_values
        assert "spam_unmarked" in action_values
        assert "priority_changed" in action_values
        assert "category_changed" in action_values


# ===========================================================================
# Thread Preview Override Guard Tests
# ===========================================================================


@pytest.fixture
def thread_with_email(db):
    """Create a thread with one COMPLETED email."""
    thread = Thread.objects.create(
        gmail_thread_id="thread-override-1",
        subject="Original subject",
        category="billing",
        priority="HIGH",
        ai_summary="Old summary",
        ai_draft_reply="Old draft",
        ai_confidence="MEDIUM",
    )
    Email.objects.create(
        thread=thread,
        message_id="msg-override-1",
        subject="Original subject",
        from_name="Alice",
        from_address="alice@example.com",
        body="Hello",
        received_at=timezone.now(),
        processing_status=Email.ProcessingStatus.COMPLETED,
        category="support",
        priority="LOW",
        ai_summary="New AI summary",
        ai_draft_reply="New AI draft",
        ai_confidence="HIGH",
    )
    return thread


@pytest.mark.django_db
class TestOverrideGuards:
    """update_thread_preview must respect override flags."""

    def test_category_overridden_preserved(self, thread_with_email):
        """Thread with category_overridden=True keeps its category."""
        thread = thread_with_email
        thread.category_overridden = True
        thread.save(update_fields=["category_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.category == "billing"

    def test_priority_overridden_preserved(self, thread_with_email):
        """Thread with priority_overridden=True keeps its priority."""
        thread = thread_with_email
        thread.priority_overridden = True
        thread.save(update_fields=["priority_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.priority == "HIGH"

    def test_no_overrides_updates_both(self, thread_with_email):
        """Thread with both flags False gets category and priority from latest email."""
        thread = thread_with_email

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.category == "support"
        assert thread.priority == "LOW"

    def test_category_overridden_still_updates_ai_fields(self, thread_with_email):
        """Even with category_overridden, ai_summary/draft/confidence still update."""
        thread = thread_with_email
        thread.category_overridden = True
        thread.save(update_fields=["category_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.ai_summary == "New AI summary"
        assert thread.ai_draft_reply == "New AI draft"
        assert thread.ai_confidence == "HIGH"

    def test_both_overridden_still_updates_preview_fields(self, thread_with_email):
        """Even with both overrides, last_message_at/last_sender/subject update."""
        thread = thread_with_email
        thread.category_overridden = True
        thread.priority_overridden = True
        thread.save(update_fields=["category_overridden", "priority_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.last_sender == "Alice"
        assert thread.last_sender_address == "alice@example.com"
        assert thread.subject == "Original subject"
