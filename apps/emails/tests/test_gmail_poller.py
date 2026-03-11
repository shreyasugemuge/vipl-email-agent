"""Tests for GmailPoller service module.

All tests mock Google API calls entirely -- no real network.
"""

import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from conftest import make_email_message


class TestGmailPollerPoll:
    """Test GmailPoller.poll() returns EmailMessage DTOs."""

    @patch("apps.emails.services.gmail_poller.build")
    @patch("apps.emails.services.gmail_poller.service_account.Credentials.from_service_account_file")
    def test_poll_returns_email_messages(self, mock_creds, mock_build):
        from apps.emails.services.gmail_poller import GmailPoller

        # Build a sample Gmail API message response
        body_text = base64.urlsafe_b64encode(b"Hello, this is a test email.").decode()
        mock_msg = {
            "id": "msg_001",
            "threadId": "thread_001",
            "internalDate": "1710072000000",  # 2024-03-10 UTC
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "Sender Name <sender@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "body": {"data": body_text},
            },
        }

        # Mock Gmail API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock labels
        mock_service.users().labels().list().execute.return_value = {
            "labels": [{"name": "Agent/Processed", "id": "Label_1"}]
        }

        # Mock messages list
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_001"}]
        }

        # Mock message get
        mock_service.users().messages().get().execute.return_value = mock_msg

        poller = GmailPoller("/fake/path/sa.json")
        emails = poller.poll("info@vidarbhainfotech.com")

        assert len(emails) == 1
        email = emails[0]
        assert email.message_id == "msg_001"
        assert email.thread_id == "thread_001"
        assert email.sender_name == "Sender Name"
        assert email.sender_email == "sender@example.com"
        assert email.subject == "Test Subject"
        assert "Hello" in email.body
        assert email.inbox == "info@vidarbhainfotech.com"

    @patch("apps.emails.services.gmail_poller.build")
    @patch("apps.emails.services.gmail_poller.service_account.Credentials.from_service_account_file")
    def test_poll_all_multiple_inboxes(self, mock_creds, mock_build):
        from apps.emails.services.gmail_poller import GmailPoller

        body_text = base64.urlsafe_b64encode(b"Test body").decode()
        mock_msg = {
            "id": "msg_002",
            "threadId": "thread_002",
            "internalDate": "1710072000000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Subject"},
                ],
                "body": {"data": body_text},
            },
        }

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.users().labels().list().execute.return_value = {
            "labels": [{"name": "Agent/Processed", "id": "Label_1"}]
        }
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_002"}]
        }
        mock_service.users().messages().get().execute.return_value = mock_msg

        poller = GmailPoller("/fake/path/sa.json")
        inboxes = ["info@vidarbhainfotech.com", "sales@vidarbhainfotech.com"]
        emails = poller.poll_all(inboxes)

        # Should have results from both inboxes (mock returns same msg for both)
        assert len(emails) == 2

    @patch("apps.emails.services.gmail_poller.build")
    @patch("apps.emails.services.gmail_poller.service_account.Credentials.from_service_account_file")
    def test_mark_processed_applies_label(self, mock_creds, mock_build):
        from apps.emails.services.gmail_poller import GmailPoller

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.users().labels().list().execute.return_value = {
            "labels": [{"name": "Agent/Processed", "id": "Label_1"}]
        }
        # Return empty messages list so poll doesn't try to parse
        mock_service.users().messages().list().execute.return_value = {"messages": []}

        poller = GmailPoller("/fake/path/sa.json")
        # Need to populate the label cache by calling poll first
        poller.poll("info@vidarbhainfotech.com")

        email_msg = make_email_message(inbox="info@vidarbhainfotech.com", message_id="msg_123")
        poller.mark_processed(email_msg)

        # Verify modify was called with the right label
        mock_service.users().messages().modify.assert_called()

    @patch("apps.emails.services.gmail_poller.build")
    @patch("apps.emails.services.gmail_poller.service_account.Credentials.from_service_account_file")
    def test_parse_message_extracts_fields(self, mock_creds, mock_build):
        from apps.emails.services.gmail_poller import GmailPoller

        body_text = base64.urlsafe_b64encode(b"Parsed body content").decode()
        msg_data = {
            "id": "msg_parse_001",
            "threadId": "thread_parse_001",
            "internalDate": "1710072000000",
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [
                    {"name": "From", "value": "Parsed Sender <parsed@test.com>"},
                    {"name": "Subject", "value": "Parsed Subject Line"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": body_text},
                    },
                    {
                        "mimeType": "application/pdf",
                        "filename": "report.pdf",
                        "body": {
                            "attachmentId": "att_001",
                            "size": 12345,
                        },
                    },
                ],
            },
        }

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        poller = GmailPoller("/fake/path/sa.json")
        email = poller._parse_message(mock_service, msg_data, "info@vidarbhainfotech.com")

        assert email is not None
        assert email.message_id == "msg_parse_001"
        assert email.thread_id == "thread_parse_001"
        assert email.sender_name == "Parsed Sender"
        assert email.sender_email == "parsed@test.com"
        assert email.subject == "Parsed Subject Line"
        assert "Parsed body content" in email.body
        assert email.attachment_count == 1
        assert "report.pdf" in email.attachment_names
        assert email.gmail_link.startswith("https://mail.google.com/")

    @patch("apps.emails.services.gmail_poller.build")
    @patch("apps.emails.services.gmail_poller.service_account.Credentials.from_service_account_file")
    def test_gmail_link_construction(self, mock_creds, mock_build):
        from apps.emails.services.gmail_poller import GmailPoller

        msg_data = {
            "id": "msg_link_001",
            "threadId": "thread_link_001",
            "internalDate": "1710072000000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Link Test"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"body").decode()},
            },
        }

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        poller = GmailPoller("/fake/path/sa.json")
        email = poller._parse_message(mock_service, msg_data, "info@vidarbhainfotech.com")

        assert email.gmail_link == "https://mail.google.com/mail/u/?authuser=info@vidarbhainfotech.com#inbox/thread_link_001"
