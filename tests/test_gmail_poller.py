"""Tests for agent/gmail_poller.py — message parsing, no real Gmail API calls."""

import base64
from unittest.mock import patch, MagicMock

from agent.gmail_poller import GmailPoller, EmailMessage


# Build a mock poller without hitting Google APIs
@patch("agent.gmail_poller.service_account.Credentials.from_service_account_file")
@patch("agent.gmail_poller.build")
def _make_poller(mock_build, mock_creds):
    return GmailPoller(service_account_key_path="/tmp/fake-sa.json")


class TestParseMessage:
    """Test _parse_message with synthetic Gmail API responses."""

    def _make_msg_data(self, from_header="John Doe <john@example.com>",
                       subject="Test Email", body_text="Hello world",
                       thread_id="thread_123", msg_id="msg_456",
                       internal_date="1709000000000", attachments=None):
        payload = {
            "headers": [
                {"name": "From", "value": from_header},
                {"name": "Subject", "value": subject},
            ],
            "mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(body_text.encode()).decode()},
        }
        if attachments:
            payload["parts"] = []
            for name in attachments:
                payload["parts"].append({"filename": name, "mimeType": "application/octet-stream", "body": {"size": 1024}})

        return {
            "id": msg_id,
            "threadId": thread_id,
            "internalDate": internal_date,
            "payload": payload,
        }

    def test_basic_parse(self):
        poller = _make_poller()
        msg_data = self._make_msg_data()
        service = MagicMock()

        result = poller._parse_message(service, msg_data, "info@test.com")

        assert isinstance(result, EmailMessage)
        assert result.sender_name == "John Doe"
        assert result.sender_email == "john@example.com"
        assert result.subject == "Test Email"
        assert "Hello world" in result.body
        assert result.thread_id == "thread_123"
        assert result.message_id == "msg_456"
        assert result.inbox == "info@test.com"

    def test_sender_without_name(self):
        poller = _make_poller()
        msg_data = self._make_msg_data(from_header="noreply@example.com")
        service = MagicMock()

        result = poller._parse_message(service, msg_data, "info@test.com")

        assert result.sender_email == "noreply@example.com"
        assert result.sender_name == "noreply"

    def test_no_subject(self):
        poller = _make_poller()
        msg_data = self._make_msg_data()
        # Remove Subject header
        msg_data["payload"]["headers"] = [h for h in msg_data["payload"]["headers"] if h["name"] != "Subject"]
        service = MagicMock()

        result = poller._parse_message(service, msg_data, "info@test.com")

        assert result.subject == "(no subject)"

    def test_body_truncation(self):
        poller = _make_poller()
        long_body = "A" * 3000
        msg_data = self._make_msg_data(body_text=long_body)
        service = MagicMock()

        result = poller._parse_message(service, msg_data, "info@test.com")

        assert len(result.body) < 3000
        assert "[...truncated...]" in result.body

    def test_gmail_link_format(self):
        poller = _make_poller()
        msg_data = self._make_msg_data(thread_id="abc123")
        service = MagicMock()

        result = poller._parse_message(service, msg_data, "info@test.com")

        assert "info@test.com" in result.gmail_link
        assert "abc123" in result.gmail_link


class TestExtractBody:
    """Test _extract_body with various payload structures."""

    def test_plain_text(self):
        poller = _make_poller()
        payload = {
            "mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(b"plain text body").decode()},
        }
        assert poller._extract_body(payload) == "plain text body"

    def test_multipart_prefers_plain(self):
        poller = _make_poller()
        payload = {
            "mimeType": "multipart/alternative",
            "body": {},
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": base64.urlsafe_b64encode(b"plain").decode()},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": base64.urlsafe_b64encode(b"<p>html</p>").decode()},
                },
            ],
        }
        assert poller._extract_body(payload) == "plain"

    def test_html_fallback(self):
        poller = _make_poller()
        payload = {
            "mimeType": "multipart/alternative",
            "body": {},
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {"data": base64.urlsafe_b64encode(b"<p>hello</p>").decode()},
                },
            ],
        }
        result = poller._extract_body(payload)
        assert "hello" in result
        assert "<p>" not in result

    def test_empty_payload(self):
        poller = _make_poller()
        assert poller._extract_body({}) == ""


class TestStripHtml:
    """Test _strip_html static method."""

    def test_removes_tags(self):
        assert "hello" in GmailPoller._strip_html("<p>hello</p>")
        assert "<p>" not in GmailPoller._strip_html("<p>hello</p>")

    def test_removes_scripts(self):
        html = "<script>alert('xss')</script><p>content</p>"
        result = GmailPoller._strip_html(html)
        assert "alert" not in result
        assert "content" in result

    def test_removes_styles(self):
        html = "<style>body{color:red}</style><p>text</p>"
        result = GmailPoller._strip_html(html)
        assert "color" not in result
        assert "text" in result


class TestFindAttachments:
    """Test _find_attachments recursive finder."""

    def test_single_attachment(self):
        poller = _make_poller()
        payload = {"filename": "doc.pdf", "mimeType": "application/pdf", "body": {"size": 1024, "attachmentId": "abc"}}
        names, details = [], []
        poller._find_attachments(payload, names, details)
        assert names == ["doc.pdf"]
        assert len(details) == 1
        assert details[0]["attachment_id"] == "abc"
        assert details[0]["mime_type"] == "application/pdf"

    def test_nested_attachments(self):
        poller = _make_poller()
        payload = {
            "mimeType": "multipart/mixed",
            "filename": "",
            "parts": [
                {"filename": "file1.pdf", "mimeType": "application/pdf", "body": {"size": 100, "attachmentId": "a1"}},
                {"filename": "file2.png", "mimeType": "image/png", "body": {"size": 200, "attachmentId": "a2"}},
                {"filename": "", "mimeType": "text/plain", "body": {"data": "dGVzdA=="}},
            ],
        }
        names, details = [], []
        poller._find_attachments(payload, names, details)
        assert "file1.pdf" in names
        assert "file2.png" in names
        assert len(names) == 2
        assert len(details) == 2

    def test_no_attachments(self):
        poller = _make_poller()
        payload = {"mimeType": "text/plain", "body": {"data": "dGVzdA=="}}
        names, details = [], []
        poller._find_attachments(payload, names, details)
        assert names == []
        assert details == []
