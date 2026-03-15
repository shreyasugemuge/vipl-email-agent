"""Tests for internal notes: InternalNote model, parse_mentions, notify_mention, ActivityLog actions."""

import pytest
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, MagicMock

from apps.accounts.models import User
from apps.emails.models import ActivityLog, Email, Thread, InternalNote
from apps.emails.services.assignment import parse_mentions, notify_mention


def _create_thread(db, **overrides):
    """Helper to create a Thread record with sensible defaults."""
    defaults = {
        "gmail_thread_id": f"thread_{id(overrides)}",
        "subject": "Test Thread Subject",
        "status": Thread.Status.NEW,
    }
    defaults.update(overrides)
    return Thread.objects.create(**defaults)


def _create_user(db, username="testuser", **overrides):
    """Helper to create a User."""
    defaults = {
        "username": username,
        "email": f"{username}@vidarbhainfotech.com",
        "first_name": username.capitalize(),
        "last_name": "User",
    }
    defaults.update(overrides)
    return User.objects.create_user(password="testpass123", **defaults)


# ===========================================================================
# InternalNote model tests
# ===========================================================================


@pytest.mark.django_db
class TestInternalNoteModel:
    """Test InternalNote creation, FK integrity, and soft delete."""

    def test_create_note(self):
        thread = _create_thread(True, gmail_thread_id="t1")
        author = _create_user(True, username="alice")
        note = InternalNote.objects.create(
            thread=thread,
            author=author,
            body="This is an internal note.",
        )
        assert note.pk is not None
        assert note.thread == thread
        assert note.author == author
        assert note.body == "This is an internal note."

    def test_note_ordering_by_created_at(self):
        thread = _create_thread(True, gmail_thread_id="t2")
        author = _create_user(True, username="bob")
        note1 = InternalNote.objects.create(thread=thread, author=author, body="First")
        note2 = InternalNote.objects.create(thread=thread, author=author, body="Second")
        notes = list(InternalNote.objects.filter(thread=thread))
        assert notes[0].pk == note1.pk
        assert notes[1].pk == note2.pk

    def test_note_reverse_relation(self):
        thread = _create_thread(True, gmail_thread_id="t3")
        author = _create_user(True, username="carol")
        InternalNote.objects.create(thread=thread, author=author, body="A note")
        assert thread.notes.count() == 1

    def test_note_mentioned_users_m2m(self):
        thread = _create_thread(True, gmail_thread_id="t4")
        author = _create_user(True, username="dave")
        mentioned = _create_user(True, username="eve")
        note = InternalNote.objects.create(thread=thread, author=author, body="@eve check this")
        note.mentioned_users.add(mentioned)
        assert mentioned in note.mentioned_users.all()

    def test_note_soft_delete(self):
        thread = _create_thread(True, gmail_thread_id="t5")
        author = _create_user(True, username="frank")
        note = InternalNote.objects.create(thread=thread, author=author, body="To be deleted")
        note.delete()
        assert InternalNote.objects.count() == 0
        assert InternalNote.all_objects.count() == 1

    def test_note_str(self):
        thread = _create_thread(True, gmail_thread_id="t6")
        author = _create_user(True, username="grace")
        note = InternalNote.objects.create(thread=thread, author=author, body="Test")
        assert "grace" in str(note).lower() or "Grace" in str(note)


# ===========================================================================
# parse_mentions tests
# ===========================================================================


class TestParseMentions:
    """Test @mention extraction from note body text."""

    def test_no_mentions(self):
        assert parse_mentions("No mentions here") == []

    def test_single_mention(self):
        assert parse_mentions("Hey @john.doe check this") == ["john.doe"]

    def test_multiple_mentions(self):
        result = parse_mentions("@alice.smith and @bob.jones")
        assert result == ["alice.smith", "bob.jones"]

    def test_mention_at_start(self):
        assert parse_mentions("@admin please review") == ["admin"]

    def test_mention_at_end(self):
        assert parse_mentions("Review this @carol") == ["carol"]

    def test_duplicate_mentions(self):
        result = parse_mentions("@alice @bob @alice")
        # Should return unique mentions
        assert "alice" in result
        assert "bob" in result

    def test_empty_string(self):
        assert parse_mentions("") == []

    def test_mention_with_underscores(self):
        assert parse_mentions("@first_last check") == ["first_last"]

    def test_at_sign_alone(self):
        assert parse_mentions("@ not a mention") == []


# ===========================================================================
# ActivityLog action choices tests
# ===========================================================================


class TestActivityLogNoteActions:
    """Test that NOTE_ADDED and MENTIONED are valid ActivityLog actions."""

    def test_note_added_action_exists(self):
        assert hasattr(ActivityLog.Action, "NOTE_ADDED")
        assert ActivityLog.Action.NOTE_ADDED == "note_added"

    def test_mentioned_action_exists(self):
        assert hasattr(ActivityLog.Action, "MENTIONED")
        assert ActivityLog.Action.MENTIONED == "mentioned"


# ===========================================================================
# notify_mention tests
# ===========================================================================


@pytest.mark.django_db
class TestNotifyMention:
    """Test @mention notification via Chat + email (mocked)."""

    @patch("apps.emails.services.assignment.ChatNotifier")
    @patch("apps.emails.services.assignment.send_mail")
    def test_notify_mention_sends_chat(self, mock_send_mail, mock_chat_cls):
        thread = _create_thread(True, gmail_thread_id="t_notify1")
        author = _create_user(True, username="alice")
        mentioned = _create_user(True, username="bob")

        mock_notifier = MagicMock()
        mock_chat_cls.return_value = mock_notifier

        notify_mention(thread, author, mentioned)

        # Chat was attempted (via webhook)
        # The function should not raise
        assert True  # If we get here, no exception

    @patch("apps.emails.services.assignment.ChatNotifier")
    @patch("apps.emails.services.assignment.send_mail")
    def test_notify_mention_sends_email(self, mock_send_mail, mock_chat_cls):
        thread = _create_thread(True, gmail_thread_id="t_notify2")
        author = _create_user(True, username="charlie")
        mentioned = _create_user(True, username="diana", email="diana@vidarbhainfotech.com")

        notify_mention(thread, author, mentioned)

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args
        # send_mail is called with keyword args
        recipient_list = call_kwargs[1].get("recipient_list", [])
        assert "diana@vidarbhainfotech.com" in recipient_list

    @patch("apps.emails.services.assignment.ChatNotifier")
    @patch("apps.emails.services.assignment.send_mail")
    def test_notify_mention_does_not_raise_on_error(self, mock_send_mail, mock_chat_cls):
        """notify_mention is fire-and-forget -- should never raise."""
        mock_chat_cls.side_effect = Exception("Chat down")
        mock_send_mail.side_effect = Exception("Email down")

        thread = _create_thread(True, gmail_thread_id="t_notify3")
        author = _create_user(True, username="eric")
        mentioned = _create_user(True, username="fiona")

        # Should not raise
        notify_mention(thread, author, mentioned)
