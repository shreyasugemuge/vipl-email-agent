"""Tests for ChatNotifier -- Google Chat webhook notifications."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.emails.services.chat_notifier import ChatNotifier


class TestChatNotifierInit:
    def test_init_with_webhook_url(self):
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier.webhook_url == "https://chat.googleapis.com/test"

    def test_init_strips_whitespace(self):
        notifier = ChatNotifier(webhook_url="  https://chat.googleapis.com/test  ")
        assert notifier.webhook_url == "https://chat.googleapis.com/test"

    def test_init_empty_url(self):
        notifier = ChatNotifier(webhook_url="")
        assert notifier.webhook_url == ""


@pytest.mark.django_db
class TestNotifyNewEmails:
    def _make_email(self, **kwargs):
        """Create a mock Email model instance."""
        defaults = {
            "subject": "Test Email Subject",
            "from_address": "sender@example.com",
            "to_inbox": "info@vidarbhainfotech.com",
            "priority": "HIGH",
            "category": "Sales Lead",
            "ai_suggested_assignee": "Shreyas",
            "ai_summary": "A test summary",
        }
        defaults.update(kwargs)
        mock_email = MagicMock()
        for k, v in defaults.items():
            setattr(mock_email, k, v)
        return mock_email

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_new_emails_posts_to_webhook(self, mock_config_cls, mock_post):
        """Verify httpx.post is called with correct webhook URL and Cards v2 payload."""
        mock_config_cls.get.return_value = None  # No quiet hours
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        emails = [self._make_email(), self._make_email(priority="CRITICAL")]
        result = notifier.notify_new_emails(emails)

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0] == "https://chat.googleapis.com/test"
        payload = call_kwargs.kwargs["json"]
        assert "cardsV2" in payload

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_quiet_hours_suppresses_notification(self, mock_config_cls, mock_post):
        """Verify httpx.post is NOT called during quiet hours."""
        # Simulate quiet hours: 20:00 to 08:00 IST
        def config_side_effect(key, default=None):
            mapping = {
                "quiet_hours_start": "20:00",
                "quiet_hours_end": "08:00",
                "tracker_url": "https://triage.vidarbhainfotech.com",
            }
            return mapping.get(key, default)

        mock_config_cls.get.side_effect = config_side_effect

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        # Patch _is_quiet_hours to return True
        with patch.object(notifier, "_is_quiet_hours", return_value=True):
            result = notifier.notify_new_emails([self._make_email()])

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_webhook_failure_logged_not_raised(self, mock_config_cls, mock_post):
        """Verify webhook failure is logged but no exception propagated."""
        mock_config_cls.get.return_value = None
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        # Should not raise
        result = notifier.notify_new_emails([self._make_email()])
        assert result is False

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_card_format_has_required_fields(self, mock_config_cls, mock_post):
        """Verify the Cards v2 structure has header, sections, and button."""
        mock_config_cls.get.return_value = None
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_new_emails([
            self._make_email(priority="CRITICAL"),
            self._make_email(priority="HIGH"),
        ])

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        assert "header" in card
        assert "sections" in card
        # Button section should have "Open Tracker"
        sections = card["sections"]
        button_found = False
        for section in sections:
            for widget in section.get("widgets", []):
                if "buttonList" in widget:
                    buttons = widget["buttonList"]["buttons"]
                    for btn in buttons:
                        if "Open Tracker" in btn.get("text", ""):
                            button_found = True
        assert button_found, "Expected 'Open Tracker' button in card"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_empty_emails_list_skips(self, mock_config_cls, mock_post):
        """No notification for empty list."""
        mock_config_cls.get.return_value = None
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        result = notifier.notify_new_emails([])
        assert result is True
        mock_post.assert_not_called()
