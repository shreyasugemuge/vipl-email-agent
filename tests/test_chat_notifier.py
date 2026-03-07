"""Tests for agent/chat_notifier.py — all mocked, no external services."""

from unittest.mock import patch, MagicMock

from agent.chat_notifier import ChatNotifier


class TestPost:
    """Test the _post() method."""

    @patch("agent.chat_notifier.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier._post({"text": "hello"}) is True
        mock_post.assert_called_once()

    @patch("agent.chat_notifier.httpx.post")
    def test_non_200_returns_false(self, mock_post):
        mock_post.return_value = MagicMock(status_code=400, text="bad request")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier._post({"text": "hello"}) is False

    def test_empty_url_returns_false(self):
        notifier = ChatNotifier(webhook_url="")
        assert notifier._post({"text": "hello"}) is False

    @patch("agent.chat_notifier.httpx.post", side_effect=Exception("connection error"))
    def test_exception_returns_false(self, mock_post):
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier._post({"text": "hello"}) is False


class TestNotifyStartup:
    """Test notify_startup()."""

    @patch("agent.chat_notifier.httpx.post")
    def test_sends_correct_payload(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        result = notifier.notify_startup(["info@test.com", "sales@test.com"], 300)

        assert result is True
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "info@test.com" in payload["text"]
        assert "300" in payload["text"]


class TestNotifyPollSummary:
    """Test notify_poll_summary()."""

    def test_empty_list_returns_true(self):
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier.notify_poll_summary([]) is True

    @patch("agent.chat_notifier.httpx.post")
    def test_sends_card_with_items(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        items = [
            {"priority": "HIGH", "ticket": "INF-0001", "subject": "Test", "category": "Sales Lead", "assignee": "Shreyas"},
            {"priority": "LOW", "ticket": "INF-0002", "subject": "Test 2", "category": "Vendor", "assignee": "EA"},
        ]
        result = notifier.notify_poll_summary(items)

        assert result is True
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "cardsV2" in payload

    @patch("agent.chat_notifier.httpx.post")
    def test_caps_at_10_items(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        items = [
            {"priority": "MEDIUM", "ticket": f"INF-{i:04d}", "subject": f"Test {i}", "category": "General Inquiry", "assignee": ""}
            for i in range(15)
        ]
        result = notifier.notify_poll_summary(items)

        assert result is True
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        card = payload["cardsV2"][0]["card"]
        # First section has the email widgets — 10 items + 1 "...and N more"
        widgets = card["sections"][0]["widgets"]
        assert len(widgets) == 11


class TestNotifySlaSummary:
    """Test notify_sla_summary()."""

    def test_empty_list_returns_true(self):
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier.notify_sla_summary([]) is True

    @patch("agent.chat_notifier.httpx.post")
    def test_sorts_by_hours_overdue(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        tickets = [
            {"Ticket #": "INF-0001", "Subject": "Minor", "Assigned To": "A", "hours_overdue": 2.0},
            {"Ticket #": "INF-0002", "Subject": "Major", "Assigned To": "B", "hours_overdue": 10.0},
        ]
        notifier.notify_sla_summary(tickets)

        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        card = payload["cardsV2"][0]["card"]
        widgets = card["sections"][0]["widgets"]
        # First widget should be the worst overdue (INF-0002)
        assert "INF-0002" in widgets[0]["decoratedText"]["text"]


class TestNotifyEodSummary:
    """Test notify_eod_summary()."""

    @patch("agent.chat_notifier.httpx.post")
    def test_sends_eod_card(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test", sheet_url="https://sheets.test")

        stats = {
            "date": "07 Mar 2026",
            "received_today": 5,
            "closed_today": 2,
            "total_open": 10,
            "sla_breaches": 1,
            "unassigned": 3,
        }
        result = notifier.notify_eod_summary(stats)

        assert result is True
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "cardsV2" in payload
