"""Tests for cross-inbox email deduplication (INBOX-02).

When the same email arrives on info@ and sales@ within 5 minutes,
the second copy is detected as a cross-inbox duplicate, skips AI triage
and spam filter, and reuses the first copy's triage result.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from conftest import make_email_message, make_triage_result


@pytest.mark.django_db
class TestCrossInboxDedup:
    """Test _detect_cross_inbox_duplicate and pipeline handling."""

    def test_cross_inbox_duplicate_detected(self):
        """Email on sales@ with same thread_id + sender as recent info@ email is detected as dup."""
        from apps.emails.services.pipeline import save_email_to_db, _detect_cross_inbox_duplicate

        # First email arrives on info@
        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_dup_001", message_id="msg_dup_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result(category="Sales Lead", priority="HIGH")
        save_email_to_db(email_msg1, triage)

        # Same email arrives on sales@ 2 minutes later
        email_msg2 = make_email_message(
            thread_id="thread_dup_001", message_id="msg_dup_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=2),
        )
        original = _detect_cross_inbox_duplicate(email_msg2)
        assert original is not None
        assert original.to_inbox == "info@vidarbhainfotech.com"

    def test_cross_inbox_duplicate_skips_ai_triage(self):
        """Cross-inbox duplicate skips AI triage, reuses first copy's triage result."""
        from apps.emails.services.pipeline import save_email_to_db, process_single_email
        from apps.emails.models import Email

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_skip_ai_001", message_id="msg_skip_ai_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result(category="Sales Lead", priority="HIGH", summary="Original summary")
        save_email_to_db(email_msg1, triage)

        # Duplicate on sales@
        email_msg2 = make_email_message(
            thread_id="thread_skip_ai_001", message_id="msg_skip_ai_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        mock_ai = MagicMock()
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock()

        result = process_single_email(
            email_msg2, mock_ai, mock_poller, mock_spam_fn, ai_enabled=True, chat_enabled=False
        )

        # AI should NOT have been called
        mock_ai.process.assert_not_called()
        # Spam filter should NOT have been called
        mock_spam_fn.assert_not_called()
        # But the email should be saved with reused triage
        assert result is not None
        assert result.category == "Sales Lead"
        assert result.priority == "HIGH"

    def test_cross_inbox_duplicate_skips_spam_filter(self):
        """Cross-inbox duplicate skips spam filter."""
        from apps.emails.services.pipeline import save_email_to_db, process_single_email

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_skip_spam_001", message_id="msg_skip_spam_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_skip_spam_001", message_id="msg_skip_spam_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        mock_ai = MagicMock()
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock()

        process_single_email(
            email_msg2, mock_ai, mock_poller, mock_spam_fn, ai_enabled=True, chat_enabled=False
        )

        mock_spam_fn.assert_not_called()

    def test_cross_inbox_duplicate_saved_to_db(self):
        """Cross-inbox duplicate is saved as a separate Email record on the same Thread."""
        from apps.emails.services.pipeline import save_email_to_db, process_single_email
        from apps.emails.models import Email, Thread

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_save_dup_001", message_id="msg_save_dup_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_save_dup_001", message_id="msg_save_dup_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        mock_ai = MagicMock()
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock()

        result = process_single_email(
            email_msg2, mock_ai, mock_poller, mock_spam_fn, ai_enabled=True, chat_enabled=False
        )

        # Both emails exist in DB
        assert Email.objects.filter(message_id="msg_save_dup_001").exists()
        assert Email.objects.filter(message_id="msg_save_dup_002").exists()

        # Both on the same thread
        thread = Thread.objects.get(gmail_thread_id="thread_save_dup_001")
        assert thread.emails.count() == 2

    def test_cross_inbox_duplicate_labeled_in_gmail(self):
        """Cross-inbox duplicate is labeled in Gmail (mark_processed called)."""
        from apps.emails.services.pipeline import save_email_to_db, process_single_email

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_label_001", message_id="msg_label_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_label_001", message_id="msg_label_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        mock_ai = MagicMock()
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock()

        process_single_email(
            email_msg2, mock_ai, mock_poller, mock_spam_fn, ai_enabled=True, chat_enabled=False
        )

        mock_poller.mark_processed.assert_called_once()

    def test_within_5_minute_window_is_duplicate(self):
        """Email within 5 minutes of original counts as cross-inbox dup."""
        from apps.emails.services.pipeline import save_email_to_db, _detect_cross_inbox_duplicate

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_window_001", message_id="msg_window_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_window_001", message_id="msg_window_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=4, seconds=59),
        )

        original = _detect_cross_inbox_duplicate(email_msg2)
        assert original is not None

    def test_outside_5_minute_window_not_duplicate(self):
        """Same sender on same thread but 10 minutes later is NOT a cross-inbox dup."""
        from apps.emails.services.pipeline import save_email_to_db, _detect_cross_inbox_duplicate

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_late_001", message_id="msg_late_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_late_001", message_id="msg_late_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=10),
        )

        original = _detect_cross_inbox_duplicate(email_msg2)
        assert original is None

    def test_different_sender_not_duplicate(self):
        """Different sender on same thread is NOT a cross-inbox dup."""
        from apps.emails.services.pipeline import save_email_to_db, _detect_cross_inbox_duplicate

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_diff_001", message_id="msg_diff_001",
            inbox="info@vidarbhainfotech.com", sender_email="alice@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_diff_001", message_id="msg_diff_002",
            inbox="sales@vidarbhainfotech.com", sender_email="bob@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        original = _detect_cross_inbox_duplicate(email_msg2)
        assert original is None

    def test_duplicate_has_is_cross_inbox_duplicate_attr(self):
        """Processed cross-inbox duplicate has _is_cross_inbox_duplicate=True."""
        from apps.emails.services.pipeline import save_email_to_db, process_single_email

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_attr_dup_001", message_id="msg_attr_dup_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        email_msg2 = make_email_message(
            thread_id="thread_attr_dup_001", message_id="msg_attr_dup_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        mock_ai = MagicMock()
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock()

        result = process_single_email(
            email_msg2, mock_ai, mock_poller, mock_spam_fn, ai_enabled=True, chat_enabled=False
        )

        assert getattr(result, "_is_cross_inbox_duplicate", False) is True

    def test_non_duplicate_has_is_cross_inbox_duplicate_false(self):
        """Normal email has _is_cross_inbox_duplicate=False."""
        from apps.emails.services.pipeline import process_single_email

        email_msg = make_email_message(
            thread_id="thread_normal_001", message_id="msg_normal_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
        )

        mock_ai = MagicMock()
        mock_ai.process.return_value = make_triage_result()
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn, ai_enabled=True, chat_enabled=False
        )

        assert getattr(result, "_is_cross_inbox_duplicate", True) is False

    def test_poll_cycle_routes_duplicates_to_notify_cross_inbox_duplicate(self):
        """process_poll_cycle calls notify_cross_inbox_duplicate for detected duplicates."""
        from apps.emails.services.pipeline import save_email_to_db, process_poll_cycle

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        # Pre-create an email on info@
        email_msg1 = make_email_message(
            thread_id="thread_poll_dup_001", message_id="msg_poll_dup_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        # Second email (duplicate on sales@)
        email_msg2 = make_email_message(
            thread_id="thread_poll_dup_001", message_id="msg_poll_dup_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        mock_poller = MagicMock()
        mock_poller.poll_all.return_value = [email_msg2]
        mock_ai = MagicMock()
        mock_ai.process.return_value = make_triage_result()
        mock_chat = MagicMock()
        mock_state = MagicMock()
        mock_state.consecutive_failures = 0

        with patch("apps.emails.services.pipeline.SystemConfig") as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                "ai_triage_enabled": True,
                "chat_notifications_enabled": True,
                "monitored_inboxes": "info@vidarbhainfotech.com,sales@vidarbhainfotech.com",
                "max_consecutive_failures": 3,
                "operating_mode": "production",
            }.get(key, default)

            process_poll_cycle(mock_poller, mock_ai, mock_chat, mock_state)

        mock_chat.notify_cross_inbox_duplicate.assert_called_once()


@pytest.mark.django_db
class TestNotifyCrossInboxDuplicate:
    """Test ChatNotifier.notify_cross_inbox_duplicate lightweight notification."""

    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_sends_lightweight_card(self, mock_config_cls):
        """notify_cross_inbox_duplicate sends a card with 'also received on' message."""
        from apps.emails.services.chat_notifier import ChatNotifier

        mock_config_cls.get.side_effect = lambda key, default=None: {
            "tracker_url": "https://triage.vidarbhainfotech.com",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
        }.get(key, default)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        # Create mock email object
        mock_thread = MagicMock()
        mock_thread.subject = "Important client inquiry"
        mock_email = MagicMock()
        mock_email.thread = mock_thread
        mock_email.to_inbox = "sales@vidarbhainfotech.com"
        mock_email.pk = 42

        with patch.object(notifier, "_post", return_value=True) as mock_post:
            result = notifier.notify_cross_inbox_duplicate(mock_email)

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        card = payload["cardsV2"][0]["card"]
        assert "Also received on" in card["header"]["title"]
        assert "sales@" in card["header"]["title"]

    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_respects_quiet_hours(self, mock_config_cls):
        """notify_cross_inbox_duplicate returns False during quiet hours."""
        from apps.emails.services.chat_notifier import ChatNotifier

        mock_config_cls.get.side_effect = lambda key, default=None: {
            "tracker_url": "https://triage.vidarbhainfotech.com",
            "quiet_hours_start": "00:00",
            "quiet_hours_end": "23:59",
        }.get(key, default)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        mock_email = MagicMock()
        mock_email.thread = MagicMock()
        mock_email.to_inbox = "sales@vidarbhainfotech.com"
        mock_email.pk = 42

        # Pin IST time to 12:00 so it's always within 00:00-23:59 quiet hours
        from datetime import datetime as _dt
        import pytz
        fixed_noon = _dt(2026, 3, 15, 12, 0, 0, tzinfo=pytz.timezone("Asia/Kolkata"))
        with patch("apps.emails.services.chat_notifier.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_noon
            mock_datetime.strptime = _dt.strptime
            with patch.object(notifier, "_post") as mock_post:
                result = notifier.notify_cross_inbox_duplicate(mock_email)

        assert result is False
        mock_post.assert_not_called()


@pytest.mark.django_db
class TestCrossInboxDedupEdgeCases:
    """Edge case tests for cross-inbox dedup (FIX-02 verification)."""

    def test_dedup_same_inbox_not_detected(self):
        """Same email arriving twice in same inbox is NOT cross-inbox duplicate.

        The query excludes same-inbox matches via .exclude(to_inbox=email_msg.inbox).
        """
        from apps.emails.services.pipeline import save_email_to_db, _detect_cross_inbox_duplicate

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_same_inbox_001", message_id="msg_same_inbox_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        # Same inbox, same thread, same sender -- NOT cross-inbox
        email_msg2 = make_email_message(
            thread_id="thread_same_inbox_001", message_id="msg_same_inbox_002",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=1),
        )

        original = _detect_cross_inbox_duplicate(email_msg2)
        assert original is None

    def test_dedup_just_outside_window_boundary(self):
        """Email at exactly 5min + 1sec after original is NOT a duplicate.

        Exercises the boundary condition: window is 5 minutes, cutoff = timestamp - 5min.
        """
        from apps.emails.services.pipeline import save_email_to_db, _detect_cross_inbox_duplicate

        ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        email_msg1 = make_email_message(
            thread_id="thread_boundary_001", message_id="msg_boundary_001",
            inbox="info@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts,
        )
        triage = make_triage_result()
        save_email_to_db(email_msg1, triage)

        # 5 min 1 sec later on different inbox
        email_msg2 = make_email_message(
            thread_id="thread_boundary_001", message_id="msg_boundary_002",
            inbox="sales@vidarbhainfotech.com", sender_email="client@example.com",
            timestamp=ts + timedelta(minutes=5, seconds=1),
        )

        original = _detect_cross_inbox_duplicate(email_msg2)
        assert original is None
