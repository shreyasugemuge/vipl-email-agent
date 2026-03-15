"""Tests for spam feedback loop: mark spam/not-spam, reputation tracking, auto-block, pipeline integration."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.emails.models import (
    ActivityLog, Email, SenderReputation, SpamFeedback, SpamWhitelist, Thread,
)
from conftest import create_email, create_thread, make_email_message, make_triage_result


@pytest.fixture
def thread_with_email(db):
    """Create a thread with one email attached."""
    thread = create_thread(last_sender_address="spammer@example.com")
    email = create_email(
        thread=thread,
        from_address="spammer@example.com",
        is_spam=False,
    )
    return thread, email


@pytest.fixture
def spam_thread_with_email(db):
    """Create a thread with one spam email attached."""
    thread = create_thread(last_sender_address="spammer@example.com")
    email = create_email(
        thread=thread,
        from_address="spammer@example.com",
        is_spam=True,
    )
    return thread, email


# ---------------------------------------------------------------------------
# mark_spam view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mark_spam_creates_feedback(admin_user, client, thread_with_email):
    """POST to mark_spam creates SpamFeedback with user_verdict=True, updates Email.is_spam, creates ActivityLog."""
    thread, email = thread_with_email
    client.force_login(admin_user)

    url = reverse("emails:mark_spam", args=[thread.pk])
    response = client.post(url)

    assert response.status_code == 200

    # SpamFeedback created
    fb = SpamFeedback.objects.get(thread=thread)
    assert fb.user == admin_user
    assert fb.user_verdict is True
    assert fb.original_verdict is False  # email was not spam originally

    # Email updated
    email.refresh_from_db()
    assert email.is_spam is True

    # ActivityLog created
    log = ActivityLog.objects.filter(
        thread=thread, action=ActivityLog.Action.SPAM_MARKED
    ).first()
    assert log is not None
    assert log.user == admin_user


@pytest.mark.django_db
def test_mark_not_spam_creates_feedback(admin_user, client, spam_thread_with_email):
    """POST to mark_not_spam creates SpamFeedback with user_verdict=False, updates Email.is_spam."""
    thread, email = spam_thread_with_email
    client.force_login(admin_user)

    url = reverse("emails:mark_not_spam", args=[thread.pk])
    response = client.post(url)

    assert response.status_code == 200

    fb = SpamFeedback.objects.get(thread=thread)
    assert fb.user_verdict is False
    assert fb.original_verdict is True  # was spam

    email.refresh_from_db()
    assert email.is_spam is False

    log = ActivityLog.objects.filter(
        thread=thread, action=ActivityLog.Action.SPAM_UNMARKED
    ).first()
    assert log is not None


@pytest.mark.django_db
def test_mark_not_spam_blocked_sender_auto_whitelists(admin_user, client, spam_thread_with_email):
    """When sender is blocked, marking not-spam creates SpamWhitelist entry."""
    thread, email = spam_thread_with_email

    # Pre-create a blocked sender reputation
    SenderReputation.objects.create(
        sender_address="spammer@example.com",
        total_count=5,
        spam_count=5,
        is_blocked=True,
    )

    client.force_login(admin_user)
    url = reverse("emails:mark_not_spam", args=[thread.pk])
    response = client.post(url)
    assert response.status_code == 200

    # Sender should be auto-whitelisted
    assert SpamWhitelist.objects.filter(entry="spammer@example.com").exists()

    # Sender should be unblocked
    rep = SenderReputation.objects.get(sender_address="spammer@example.com")
    assert rep.is_blocked is False


@pytest.mark.django_db
def test_reputation_updated_on_feedback(admin_user, client, thread_with_email):
    """mark_spam increments spam_count on SenderReputation."""
    thread, email = thread_with_email

    # Pre-create reputation
    SenderReputation.objects.create(
        sender_address="spammer@example.com",
        total_count=5,
        spam_count=1,
    )

    client.force_login(admin_user)
    url = reverse("emails:mark_spam", args=[thread.pk])
    client.post(url)

    rep = SenderReputation.objects.get(sender_address="spammer@example.com")
    assert rep.spam_count == 2


@pytest.mark.django_db
def test_auto_block_threshold(admin_user, client, thread_with_email):
    """When SenderReputation reaches spam_ratio > 0.8 AND total_count >= 3, is_blocked is set."""
    thread, email = thread_with_email

    # Pre-create reputation just below threshold: 2/3 = 0.67, after mark will be 3/3 = 1.0
    SenderReputation.objects.create(
        sender_address="spammer@example.com",
        total_count=3,
        spam_count=2,
    )

    client.force_login(admin_user)
    url = reverse("emails:mark_spam", args=[thread.pk])
    client.post(url)

    rep = SenderReputation.objects.get(sender_address="spammer@example.com")
    assert rep.spam_count == 3
    assert rep.spam_ratio > 0.8
    assert rep.is_blocked is True


@pytest.mark.django_db
def test_undo_spam_feedback(admin_user, client, thread_with_email):
    """POST to undo endpoint deletes SpamFeedback, reverses reputation change."""
    thread, email = thread_with_email

    # First mark as spam
    client.force_login(admin_user)
    client.post(reverse("emails:mark_spam", args=[thread.pk]))

    fb = SpamFeedback.objects.get(thread=thread)
    rep = SenderReputation.objects.get(sender_address="spammer@example.com")
    assert rep.spam_count == 1

    # Now undo
    url = reverse("emails:undo_spam_feedback", args=[fb.pk])
    response = client.post(url)
    assert response.status_code == 200

    # Feedback soft-deleted
    assert not SpamFeedback.objects.filter(pk=fb.pk).exists()

    # Reputation reversed
    rep.refresh_from_db()
    assert rep.spam_count == 0

    # Email reverted
    email.refresh_from_db()
    assert email.is_spam is False


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pipeline_is_blocked():
    """_is_blocked returns True for sender with is_blocked=True."""
    from apps.emails.services.pipeline import _is_blocked

    SenderReputation.objects.create(
        sender_address="blocked@example.com",
        total_count=5,
        spam_count=5,
        is_blocked=True,
    )
    assert _is_blocked("blocked@example.com") is True
    assert _is_blocked("BLOCKED@example.com") is True  # case-insensitive
    assert _is_blocked("legit@example.com") is False


@pytest.mark.django_db
def test_pipeline_skips_blocked_sender():
    """process_single_email returns None for blocked sender."""
    from unittest.mock import MagicMock
    from apps.emails.services.pipeline import process_single_email

    SenderReputation.objects.create(
        sender_address="blocked@example.com",
        total_count=5,
        spam_count=5,
        is_blocked=True,
    )

    email_msg = make_email_message(sender_email="blocked@example.com")
    result = process_single_email(
        email_msg=email_msg,
        ai_processor=MagicMock(),
        gmail_poller=MagicMock(),
        spam_filter_fn=MagicMock(),
    )
    assert result is None


@pytest.mark.django_db
def test_pipeline_increments_reputation():
    """After processing an email, SenderReputation.total_count increments."""
    from unittest.mock import MagicMock
    from apps.emails.services.pipeline import process_single_email
    from apps.emails.services.spam_filter import is_spam as spam_filter_fn

    mock_poller = MagicMock()
    mock_ai = MagicMock()
    mock_ai.process.return_value = make_triage_result(is_spam=False)

    email_msg = make_email_message(sender_email="tracked@example.com")
    process_single_email(
        email_msg=email_msg,
        ai_processor=mock_ai,
        gmail_poller=mock_poller,
        spam_filter_fn=spam_filter_fn,
    )

    rep = SenderReputation.objects.get(sender_address="tracked@example.com")
    assert rep.total_count == 1
    assert rep.spam_count == 0

    # Process a spam email (via AI returning is_spam=True)
    mock_ai2 = MagicMock()
    mock_ai2.process.return_value = make_triage_result(is_spam=True)
    email_msg2 = make_email_message(
        message_id="msg_spam_1",
        thread_id="thread_spam_1",
        sender_email="tracked@example.com",
    )
    process_single_email(
        email_msg=email_msg2,
        ai_processor=mock_ai2,
        gmail_poller=mock_poller,
        spam_filter_fn=spam_filter_fn,
    )

    rep.refresh_from_db()
    assert rep.total_count == 2
    assert rep.spam_count == 1


@pytest.mark.django_db
def test_all_users_can_mark_spam(member_user, client, thread_with_email):
    """Both admin and member roles can POST to mark_spam."""
    thread, email = thread_with_email
    client.force_login(member_user)

    url = reverse("emails:mark_spam", args=[thread.pk])
    response = client.post(url)

    # Should succeed (not 403)
    assert response.status_code == 200
    assert SpamFeedback.objects.filter(thread=thread).exists()
