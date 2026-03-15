"""Tests for inbox badge template tags (INBOX-01, INBOX-03).

Colored pill badges showing which inbox(es) an email/thread was received on.
"""

import pytest
from django.test import TestCase


@pytest.mark.django_db
class TestInboxBadge:
    """Test inbox_badge template tag for single-inbox display."""

    def test_info_inbox_returns_teal_badge(self):
        from apps.emails.templatetags.inbox_tags import inbox_badge

        result = inbox_badge("info@vidarbhainfotech.com")
        assert "info@" in result
        assert "#00695c" in result  # Teal text color
        assert "#e0f2f1" in result  # Teal bg color
        assert "inbox-badge" in result

    def test_sales_inbox_returns_amber_badge(self):
        from apps.emails.templatetags.inbox_tags import inbox_badge

        result = inbox_badge("sales@vidarbhainfotech.com")
        assert "sales@" in result
        assert "#f57f17" in result  # Amber text color
        assert "#fff8e1" in result  # Amber bg color

    def test_unknown_inbox_returns_neutral_badge(self):
        from apps.emails.templatetags.inbox_tags import inbox_badge

        result = inbox_badge("unknown@example.com")
        assert "unknown@" in result
        # Should use default purple color
        assert "#6a1b9a" in result  # Purple text
        assert "#f3e5f5" in result  # Purple bg

    def test_empty_inbox_returns_empty_string(self):
        from apps.emails.templatetags.inbox_tags import inbox_badge

        assert inbox_badge("") == ""

    def test_none_inbox_returns_empty_string(self):
        from apps.emails.templatetags.inbox_tags import inbox_badge

        assert inbox_badge(None) == ""


@pytest.mark.django_db
class TestThreadInboxBadges:
    """Test thread_inbox_badges template tag for multi-inbox threads."""

    def test_single_inbox_returns_one_badge(self):
        from apps.emails.templatetags.inbox_tags import thread_inbox_badges
        from apps.emails.models import Thread, Email
        from datetime import datetime, timezone

        thread = Thread.objects.create(
            gmail_thread_id="thread_badge_001",
            subject="Test subject",
        )
        Email.objects.create(
            thread=thread,
            message_id="msg_badge_001",
            gmail_thread_id="thread_badge_001",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test",
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

        result = thread_inbox_badges(thread)
        assert "info@" in result
        assert result.count("inbox-badge") == 1

    def test_two_inboxes_returns_two_badges(self):
        """Dedup scenario: thread has emails from both info@ and sales@."""
        from apps.emails.templatetags.inbox_tags import thread_inbox_badges
        from apps.emails.models import Thread, Email
        from datetime import datetime, timezone

        thread = Thread.objects.create(
            gmail_thread_id="thread_badge_002",
            subject="Dedup test",
        )
        Email.objects.create(
            thread=thread,
            message_id="msg_badge_002a",
            gmail_thread_id="thread_badge_002",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            subject="Test",
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        )
        Email.objects.create(
            thread=thread,
            message_id="msg_badge_002b",
            gmail_thread_id="thread_badge_002",
            from_address="sender@example.com",
            to_inbox="sales@vidarbhainfotech.com",
            subject="Test",
            received_at=datetime(2026, 3, 10, 12, 1, 0, tzinfo=timezone.utc),
        )

        result = thread_inbox_badges(thread)
        assert "info@" in result
        assert "sales@" in result
        assert result.count("inbox-badge") == 2

    def test_none_thread_returns_empty(self):
        from apps.emails.templatetags.inbox_tags import thread_inbox_badges

        assert thread_inbox_badges(None) == ""

    def test_badges_complement_vipl_plum_palette(self):
        """Badge colors should complement VIPL plum (#a83362) -- teal and amber do."""
        from apps.emails.templatetags.inbox_tags import INBOX_COLORS

        assert "info@" in INBOX_COLORS
        assert "sales@" in INBOX_COLORS
        # Teal and amber are complementary to plum
        assert INBOX_COLORS["info@"]["text"] == "#00695c"
        assert INBOX_COLORS["sales@"]["text"] == "#f57f17"
