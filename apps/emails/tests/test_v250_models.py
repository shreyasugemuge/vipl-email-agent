"""Tests for v2.5.0 models, fields, and constraints."""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    Email,
    SenderReputation,
    SpamFeedback,
    Thread,
    ThreadReadState,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser_v250",
        email="test@vidarbhainfotech.com",
        password="testpass123",
    )


@pytest.fixture
def thread(db):
    return Thread.objects.create(
        gmail_thread_id="thread-v250-001",
        subject="Test Thread for v2.5.0",
    )


@pytest.fixture
def email_obj(db, thread):
    return Email.objects.create(
        message_id="msg-v250-001@example.com",
        from_address="sender@example.com",
        to_inbox="info@vidarbhainfotech.com",
        subject="Test Email",
        body="Body",
        received_at=timezone.now(),
        thread=thread,
    )


@pytest.mark.django_db
class TestThreadReadState:
    def test_create_with_defaults(self, user, thread):
        state = ThreadReadState.objects.create(thread=thread, user=user)
        assert state.is_read is False
        assert state.read_at is None

    def test_mark_as_read(self, user, thread):
        now = timezone.now()
        state = ThreadReadState.objects.create(
            thread=thread, user=user, is_read=True, read_at=now
        )
        assert state.is_read is True
        assert state.read_at == now

    def test_unique_together_enforced(self, user, thread):
        ThreadReadState.objects.create(thread=thread, user=user)
        with pytest.raises(IntegrityError):
            ThreadReadState.objects.create(thread=thread, user=user)

    def test_soft_delete(self, user, thread):
        state = ThreadReadState.objects.create(thread=thread, user=user)
        state.delete()
        assert state.deleted_at is not None
        assert ThreadReadState.objects.count() == 0
        assert ThreadReadState.all_objects.count() == 1

    def test_str_representation(self, user, thread):
        state = ThreadReadState.objects.create(thread=thread, user=user)
        assert "unread" in str(state)
        state.is_read = True
        assert "read" in str(state)


@pytest.mark.django_db
class TestSpamFeedback:
    def test_create_with_verdicts(self, user):
        fb = SpamFeedback.objects.create(
            user=user, original_verdict=True, user_verdict=False
        )
        assert fb.original_verdict is True
        assert fb.user_verdict is False

    def test_thread_and_email_nullable(self, user):
        fb = SpamFeedback.objects.create(
            user=user, original_verdict=False, user_verdict=True
        )
        assert fb.thread is None
        assert fb.email is None

    def test_with_thread(self, user, thread):
        fb = SpamFeedback.objects.create(
            user=user, thread=thread, original_verdict=True, user_verdict=True
        )
        assert fb.thread == thread

    def test_str_representation(self, user):
        fb = SpamFeedback.objects.create(
            user=user, original_verdict=False, user_verdict=True
        )
        assert "spam" in str(fb)

        fb2 = SpamFeedback.objects.create(
            user=user, original_verdict=True, user_verdict=False
        )
        assert "not-spam" in str(fb2)


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


@pytest.mark.django_db
class TestAssignmentFeedback:
    def test_create_with_required_fields(self, user, thread):
        fb = AssignmentFeedback.objects.create(
            thread=thread,
            action=AssignmentFeedback.FeedbackAction.ACCEPTED,
            user_who_acted=user,
        )
        assert fb.thread == thread
        assert fb.action == "accepted"
        assert fb.user_who_acted == user

    def test_all_feedback_actions(self, user, thread):
        for action_value, _label in AssignmentFeedback.FeedbackAction.choices:
            fb = AssignmentFeedback.objects.create(
                thread=thread, action=action_value, user_who_acted=user
            )
            assert fb.action == action_value

    def test_optional_fields_nullable(self, user, thread):
        fb = AssignmentFeedback.objects.create(
            thread=thread,
            action=AssignmentFeedback.FeedbackAction.REJECTED,
            user_who_acted=user,
        )
        assert fb.email is None
        assert fb.suggested_user is None
        assert fb.actual_user is None
        assert fb.confidence_at_time is None

    def test_str_representation(self, user, thread):
        fb = AssignmentFeedback.objects.create(
            thread=thread,
            action=AssignmentFeedback.FeedbackAction.ACCEPTED,
            user_who_acted=user,
        )
        assert "accepted" in str(fb)


@pytest.mark.django_db
class TestThreadOverrideFields:
    def test_category_overridden_default(self, thread):
        thread.refresh_from_db()
        assert thread.category_overridden is False

    def test_priority_overridden_default(self, thread):
        thread.refresh_from_db()
        assert thread.priority_overridden is False

    def test_ai_confidence_default(self, thread):
        thread.refresh_from_db()
        assert thread.ai_confidence == ""

    def test_ai_confidence_set(self):
        t = Thread.objects.create(
            gmail_thread_id="conf-thread-001",
            subject="Confidence Test",
            ai_confidence="HIGH",
        )
        assert t.ai_confidence == "HIGH"


@pytest.mark.django_db
class TestEmailAiConfidence:
    def test_default_empty(self, email_obj):
        email_obj.refresh_from_db()
        assert email_obj.ai_confidence == ""

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
