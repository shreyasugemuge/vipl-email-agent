"""Tests for SheetsSyncService -- Google Sheets read-only sync mirror."""

from datetime import timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.utils import timezone

from apps.emails.models import Email
from apps.emails.services.sheets_sync import SheetsSyncService


@pytest.fixture
def mock_sheets_service():
    """Create a mock Google Sheets API service."""
    mock_service = MagicMock()
    mock_spreadsheets = MagicMock()
    mock_service.spreadsheets.return_value = mock_spreadsheets

    # Mock get() for tab listing
    mock_get = MagicMock()
    mock_spreadsheets.get.return_value = mock_get
    mock_get.execute.return_value = {
        "sheets": [
            {"properties": {"title": "Email Log"}},
        ]
    }

    # Mock values()
    mock_values = MagicMock()
    mock_spreadsheets.values.return_value = mock_values

    # Mock values().get() for row index
    mock_values_get = MagicMock()
    mock_values.get.return_value = mock_values_get
    mock_values_get.execute.return_value = {"values": []}

    # Mock values().append()
    mock_append = MagicMock()
    mock_values.append.return_value = mock_append
    mock_append.execute.return_value = {"updates": {"updatedRows": 1}}

    # Mock values().batchUpdate()
    mock_batch_update = MagicMock()
    mock_values.batchUpdate.return_value = mock_batch_update
    mock_batch_update.execute.return_value = {}

    # Mock batchUpdate() (spreadsheets level, for addSheet)
    mock_ss_batch_update = MagicMock()
    mock_spreadsheets.batchUpdate.return_value = mock_ss_batch_update
    mock_ss_batch_update.execute.return_value = {}

    return mock_service


@pytest.fixture
def sync_service(mock_sheets_service):
    """Create SheetsSyncService with mocked Sheets API."""
    with patch(
        "apps.emails.services.sheets_sync.build", return_value=mock_sheets_service
    ):
        service = SheetsSyncService(
            service_account_key_path="/fake/key.json",
            spreadsheet_id="fake-spreadsheet-id",
        )
    return service


@pytest.fixture
def sample_email(db):
    """Create a completed, non-spam email for testing sync."""
    return Email.objects.create(
        message_id="msg-001@example.com",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_inbox="info@vidarbhainfotech.com",
        subject="Test Subject",
        body="Test body",
        received_at=timezone.now(),
        category="Technical Support",
        priority="HIGH",
        status="new",
        processing_status="completed",
        is_spam=False,
    )


@pytest.mark.django_db
class TestEnsureTab:
    def test_ensure_tab_creates_tab(self, sync_service, mock_sheets_service):
        """When 'v2 Mirror' tab doesn't exist, creates it with header row."""
        mock_ss = mock_sheets_service.spreadsheets.return_value

        # Tab listing shows no "v2 Mirror"
        mock_ss.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "Email Log"}}]
        }

        sync_service._ensure_tab_exists()

        # Should call batchUpdate to create tab
        mock_ss.batchUpdate.assert_called_once()
        call_args = mock_ss.batchUpdate.call_args
        body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]

        # Should write header row
        mock_ss.values.return_value.update.assert_called_once()
        assert sync_service._initialized is True

    def test_ensure_tab_exists_already(self, sync_service, mock_sheets_service):
        """When tab already exists, does nothing (no error)."""
        mock_ss = mock_sheets_service.spreadsheets.return_value
        mock_ss.get.return_value.execute.return_value = {
            "sheets": [
                {"properties": {"title": "Email Log"}},
                {"properties": {"title": "v2 Mirror"}},
            ]
        }

        sync_service._ensure_tab_exists()

        # Should NOT call batchUpdate to create tab
        mock_ss.batchUpdate.assert_not_called()
        assert sync_service._initialized is True


@pytest.mark.django_db
class TestSyncEmails:
    def test_sync_new_emails(self, sync_service, mock_sheets_service, sample_email):
        """New emails (not yet synced) are appended as rows with correct column values."""
        mock_ss = mock_sheets_service.spreadsheets.return_value

        # Tab exists
        mock_ss.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "v2 Mirror"}}]
        }
        # No existing rows (empty row index)
        mock_ss.values.return_value.get.return_value.execute.return_value = {
            "values": []
        }

        sync_service.sync_changed_emails()

        # Should append rows
        mock_ss.values.return_value.append.assert_called_once()
        call_args = mock_ss.values.return_value.append.call_args
        body = call_args[1].get("body", call_args[0][-1] if len(call_args[0]) > 1 else None)
        rows = body["values"]
        assert len(rows) == 1
        assert rows[0][2] == "Test Subject"  # Column C = Subject
        assert rows[0][5] == "HIGH"  # Column F = Priority

    def test_sync_updated_emails(self, sync_service, mock_sheets_service, sample_email):
        """Emails with changed status/assignee have their rows updated."""
        mock_ss = mock_sheets_service.spreadsheets.return_value

        # Tab exists
        mock_ss.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "v2 Mirror"}}]
        }
        # Existing row for this message_id (row 2, header is row 1)
        mock_ss.values.return_value.get.return_value.execute.return_value = {
            "values": [["msg-001@example.com"]]
        }

        # Change status
        sample_email.status = "acknowledged"
        sample_email.save()

        sync_service.sync_changed_emails()

        # Should call batchUpdate for existing rows
        mock_ss.values.return_value.batchUpdate.assert_called_once()

    def test_sync_mixed(self, sync_service, mock_sheets_service, sample_email, db):
        """Mix of new and updated emails -- appends new, updates existing."""
        mock_ss = mock_sheets_service.spreadsheets.return_value

        # Create another email
        new_email = Email.objects.create(
            message_id="msg-002@example.com",
            from_address="other@example.com",
            from_name="Other Sender",
            to_inbox="info@vidarbhainfotech.com",
            subject="New Subject",
            body="New body",
            received_at=timezone.now(),
            category="Sales Inquiry",
            priority="MEDIUM",
            status="new",
            processing_status="completed",
            is_spam=False,
        )

        # Tab exists
        mock_ss.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "v2 Mirror"}}]
        }
        # Only msg-001 exists in sheet
        mock_ss.values.return_value.get.return_value.execute.return_value = {
            "values": [["msg-001@example.com"]]
        }

        sync_service.sync_changed_emails()

        # Should append new (msg-002) and update existing (msg-001)
        mock_ss.values.return_value.append.assert_called_once()
        mock_ss.values.return_value.batchUpdate.assert_called_once()

    def test_sync_failure_does_not_crash(self, sync_service, mock_sheets_service, sample_email):
        """Sheets API raises exception -- sync logs warning, returns gracefully."""
        mock_ss = mock_sheets_service.spreadsheets.return_value
        mock_ss.get.return_value.execute.side_effect = Exception("API Error")

        # Should not raise
        sync_service.sync_changed_emails()


@pytest.mark.django_db
class TestRowFormat:
    def test_row_format(self, sync_service, sample_email):
        """Email row has 10 columns in correct order."""
        row = sync_service._email_to_row(sample_email)
        assert len(row) == 10
        # Index: 0=Date, 1=From, 2=Subject, 3=Inbox, 4=Category, 5=Priority,
        #        6=Assignee, 7=Status, 8=SLA Deadline, 9=Message ID
        assert "sender@example.com" in row[1]
        assert row[2] == "Test Subject"
        assert row[3] == "info@vidarbhainfotech.com"
        assert row[4] == "Technical Support"
        assert row[5] == "HIGH"
        assert row[6] == ""  # No assignee
        assert row[7] == "new"
        assert row[9] == "msg-001@example.com"


@pytest.mark.django_db
class TestLastSynced:
    def test_last_synced_written(self, sync_service, mock_sheets_service, sample_email):
        """After successful sync, sheets_last_synced SystemConfig key is updated."""
        from apps.core.models import SystemConfig

        mock_ss = mock_sheets_service.spreadsheets.return_value
        mock_ss.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "v2 Mirror"}}]
        }
        mock_ss.values.return_value.get.return_value.execute.return_value = {
            "values": []
        }

        sync_service.sync_changed_emails()

        last_synced = SystemConfig.get("sheets_last_synced", "")
        assert last_synced != ""
        assert "T" in last_synced  # ISO format
