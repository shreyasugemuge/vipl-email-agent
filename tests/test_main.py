"""Tests for main.py — config loading, quiet hours, circuit breaker, dead letter retry."""

import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
import pytz

# Import functions under test
from main import load_config, is_quiet_hours, retry_failed_triages, process_emails, HealthHandler
from agent.state import StateManager


class TestLoadConfig:
    """Test load_config with environment variable overlays."""

    def test_loads_config_yaml(self, monkeypatch):
        monkeypatch.setenv("MONITORED_INBOXES", "info@test.com")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-id")
        monkeypatch.setenv("GOOGLE_CHAT_WEBHOOK_URL", "https://chat.googleapis.com/test")
        monkeypatch.setenv("ADMIN_EMAIL", "admin@test.com")

        config = load_config("config.yaml")

        assert config["gmail"]["inboxes"] == ["info@test.com"]
        assert config["google_sheets"]["spreadsheet_id"] == "test-id"
        assert config["admin"]["email"] == "admin@test.com"

    def test_env_overrides_yaml(self, monkeypatch):
        monkeypatch.setenv("MONITORED_INBOXES", "custom@test.com")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "custom-id")
        monkeypatch.setenv("GOOGLE_CHAT_WEBHOOK_URL", "https://chat.googleapis.com/custom")
        monkeypatch.setenv("ADMIN_EMAIL", "custom@test.com")

        config = load_config("config.yaml")

        assert "custom@test.com" in config["gmail"]["inboxes"]
        assert config["google_sheets"]["spreadsheet_id"] == "custom-id"

    def test_multiple_inboxes(self, monkeypatch):
        monkeypatch.setenv("MONITORED_INBOXES", "info@test.com, sales@test.com, support@test.com")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-id")
        monkeypatch.setenv("GOOGLE_CHAT_WEBHOOK_URL", "https://chat.googleapis.com/test")
        monkeypatch.setenv("ADMIN_EMAIL", "admin@test.com")

        config = load_config("config.yaml")

        assert len(config["gmail"]["inboxes"]) == 3

    def test_eod_recipients_default_to_admin(self, monkeypatch):
        monkeypatch.setenv("MONITORED_INBOXES", "info@test.com")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-id")
        monkeypatch.setenv("GOOGLE_CHAT_WEBHOOK_URL", "https://chat.googleapis.com/test")
        monkeypatch.setenv("ADMIN_EMAIL", "admin@test.com")
        # Don't set EOD_RECIPIENTS

        config = load_config("config.yaml")

        assert config["eod"]["recipients"] == ["admin@test.com"]

    def test_missing_required_exits(self, monkeypatch):
        # Don't set any env vars — should exit
        monkeypatch.delenv("MONITORED_INBOXES", raising=False)
        monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CHAT_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("ADMIN_EMAIL", raising=False)

        with pytest.raises(SystemExit):
            load_config("config.yaml")

    def test_missing_config_file_exits(self):
        with pytest.raises(SystemExit):
            load_config("nonexistent.yaml")


class TestIsQuietHours:
    """Test is_quiet_hours with various config scenarios."""

    def test_disabled(self):
        config = {"quiet_hours": {"enabled": False, "start_hour": 20, "end_hour": 8}}
        assert is_quiet_hours(config) is False

    def test_no_quiet_hours_config(self):
        assert is_quiet_hours({}) is False

    @patch("main.datetime")
    def test_overnight_range_during_quiet(self, mock_dt):
        """20:00 - 08:00 range, current time 22:00 — should be quiet."""
        mock_now = mock_dt.now.return_value
        mock_now.hour = 22
        config = {"quiet_hours": {"enabled": True, "start_hour": 20, "end_hour": 8}}
        assert is_quiet_hours(config) is True

    @patch("main.datetime")
    def test_overnight_range_during_active(self, mock_dt):
        """20:00 - 08:00 range, current time 14:00 — should be active."""
        mock_now = mock_dt.now.return_value
        mock_now.hour = 14
        config = {"quiet_hours": {"enabled": True, "start_hour": 20, "end_hour": 8}}
        assert is_quiet_hours(config) is False

    @patch("main.datetime")
    def test_overnight_range_early_morning(self, mock_dt):
        """20:00 - 08:00 range, current time 03:00 — should be quiet."""
        mock_now = mock_dt.now.return_value
        mock_now.hour = 3
        config = {"quiet_hours": {"enabled": True, "start_hour": 20, "end_hour": 8}}
        assert is_quiet_hours(config) is True

    @patch("main.datetime")
    def test_daytime_range_during_quiet(self, mock_dt):
        """10:00 - 14:00 range, current time 12:00 — should be quiet."""
        mock_now = mock_dt.now.return_value
        mock_now.hour = 12
        config = {"quiet_hours": {"enabled": True, "start_hour": 10, "end_hour": 14}}
        assert is_quiet_hours(config) is True

    @patch("main.datetime")
    def test_daytime_range_outside_quiet(self, mock_dt):
        """10:00 - 14:00 range, current time 16:00 — should be active."""
        mock_now = mock_dt.now.return_value
        mock_now.hour = 16
        config = {"quiet_hours": {"enabled": True, "start_hour": 10, "end_hour": 14}}
        assert is_quiet_hours(config) is False


class TestRetryFailedTriages:
    """Test the dead letter retry function."""

    def test_skips_when_ai_disabled(self):
        components = {
            "sheet": MagicMock(),
            "gmail": MagicMock(),
            "ai": MagicMock(),
            "chat": MagicMock(),
            "config": {"feature_flags": {"ai_enabled": False}},
        }
        retry_failed_triages(components)
        components["sheet"].get_failed_triages_for_retry.assert_not_called()

    def test_noop_when_no_eligible(self):
        components = {
            "sheet": MagicMock(),
            "gmail": MagicMock(),
            "ai": MagicMock(),
            "chat": MagicMock(),
            "config": {},
        }
        components["sheet"].get_failed_triages_for_retry.return_value = []
        retry_failed_triages(components)
        components["gmail"].fetch_thread_message.assert_not_called()

    def test_successful_retry_logs_email(self):
        mock_sheet = MagicMock()
        mock_gmail = MagicMock()
        mock_ai = MagicMock()

        mock_email = MagicMock()
        mock_email.timestamp = datetime.now(pytz.UTC)
        mock_gmail.fetch_thread_message.return_value = mock_email
        mock_ai.process.return_value = MagicMock(category="General Inquiry")
        mock_sheet.get_failed_triages_for_retry.return_value = [
            {"Thread ID": "t1", "Inbox": "info@test.com", "Retry Count": "0",
             "Subject": "Test", "_row_number": 2},
        ]
        mock_sheet.get_sla_config.return_value = {}
        mock_sheet.log_email.return_value = "INF-0099"

        components = {
            "sheet": mock_sheet, "gmail": mock_gmail, "ai": mock_ai,
            "chat": MagicMock(), "config": {"sla": {"defaults": {}}},
        }
        retry_failed_triages(components)

        mock_sheet.log_email.assert_called_once()
        mock_sheet.update_failed_triage_retry.assert_called_with(2, 1, "Success")

    def test_exhausted_after_third_failure(self):
        mock_sheet = MagicMock()
        mock_gmail = MagicMock()
        mock_gmail.fetch_thread_message.return_value = None  # Will cause ValueError

        mock_sheet.get_failed_triages_for_retry.return_value = [
            {"Thread ID": "t1", "Inbox": "info@test.com", "Retry Count": "2",
             "Subject": "Failing", "_row_number": 3},
        ]
        mock_sheet.get_sla_config.return_value = {}

        components = {
            "sheet": mock_sheet, "gmail": mock_gmail, "ai": MagicMock(),
            "chat": MagicMock(), "config": {"sla": {"defaults": {}}, "quiet_hours": {"enabled": False}},
        }
        retry_failed_triages(components)

        mock_sheet.update_failed_triage_retry.assert_called_with(3, 3, "Exhausted")


class TestCircuitBreaker:
    """Test that the circuit breaker prevents polling when too many failures occur."""

    def test_state_manager_failure_tracking(self):
        state = StateManager()
        assert state.consecutive_failures == 0
        state.record_failure()
        assert state.consecutive_failures == 1
        state.record_failure()
        state.record_failure()
        assert state.consecutive_failures == 3
        state.reset_failures()
        assert state.consecutive_failures == 0

    @patch("main.load_sheet_config_overrides")
    def test_circuit_breaker_skips_poll(self, mock_overrides):
        """When failures >= max, process_emails should return early."""
        state = StateManager()
        for _ in range(3):
            state.record_failure()

        config = {
            "admin": {"max_consecutive_failures": 3},
            "feature_flags": {},
            "gmail": {"inboxes": ["info@test.com"]},
            "sla": {"defaults": {}},
            "quiet_hours": {"enabled": False},
        }
        mock_overrides.return_value = config

        components = {
            "sheet": MagicMock(),
            "gmail": MagicMock(),
            "ai": MagicMock(),
            "chat": MagicMock(),
            "state": state,
            "config": config,
        }
        process_emails(components)
        # Gmail should NOT be polled when circuit breaker is open
        components["gmail"].poll_all.assert_not_called()


class TestEODDedup:
    """Test that EOD send deduplication works."""

    def test_can_send_eod_initially(self):
        state = StateManager()
        assert state.can_send_eod() is True

    def test_cannot_send_eod_after_recent_send(self):
        state = StateManager()
        state.record_eod_sent()
        assert state.can_send_eod() is False

    def test_can_send_eod_after_timeout(self):
        state = StateManager()
        state._last_eod_time = datetime(2020, 1, 1)  # Way in the past
        assert state.can_send_eod() is True


class TestMarkProcessed:
    """Test that Gmail label is applied after Sheet log, not during poll."""

    @patch("agent.gmail_poller.service_account.Credentials.from_service_account_file")
    @patch("agent.gmail_poller.build")
    def test_poll_does_not_label(self, mock_build, mock_creds):
        """poll() should return emails WITHOUT labeling them."""
        from agent.gmail_poller import GmailPoller

        poller = GmailPoller(service_account_key_path="/tmp/fake-sa.json")
        mock_service = MagicMock()
        poller._services["test@test.com"] = mock_service

        # Mock label exists
        mock_service.users().labels().list().execute.return_value = {
            "labels": [{"name": "Agent/Processed", "id": "Label_123"}]
        }
        # Mock message list
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        # Mock full message
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "internalDate": "1709000000000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test"},
                ],
                "mimeType": "text/plain",
                "body": {"data": "dGVzdA=="},
            },
        }

        emails = poller.poll("test@test.com")
        assert len(emails) == 1
        # Should NOT have called modify (label application)
        mock_service.users().messages().modify.assert_not_called()

    @patch("agent.gmail_poller.service_account.Credentials.from_service_account_file")
    @patch("agent.gmail_poller.build")
    def test_mark_processed_applies_label(self, mock_build, mock_creds):
        """mark_processed() should apply the label."""
        from agent.gmail_poller import GmailPoller, EmailMessage

        poller = GmailPoller(service_account_key_path="/tmp/fake-sa.json")
        mock_service = MagicMock()
        poller._services["test@test.com"] = mock_service
        poller._label_ids["test@test.com"] = "Label_123"

        email = EmailMessage(
            thread_id="t1", message_id="msg1", inbox="test@test.com",
            sender_name="Test", sender_email="test@test.com",
            subject="Test", body="Test", timestamp=datetime.now(),
        )
        poller.mark_processed(email)
        mock_service.users().messages().modify.assert_called_once()
