"""Tests for the run_scheduler management command."""

import signal
from unittest.mock import MagicMock, patch, call

import pytest


class TestSchedulerCommand:
    @patch("apps.emails.management.commands.run_scheduler.BlockingScheduler")
    @patch("apps.emails.management.commands.run_scheduler.GmailPoller")
    @patch("apps.emails.management.commands.run_scheduler.AIProcessor")
    @patch("apps.emails.management.commands.run_scheduler.ChatNotifier")
    @patch("apps.emails.management.commands.run_scheduler.StateManager")
    @patch("apps.emails.management.commands.run_scheduler.SystemConfig")
    @patch.dict("os.environ", {
        "GOOGLE_SERVICE_ACCOUNT_KEY_PATH": "/app/secrets/sa.json",
        "ANTHROPIC_API_KEY": "test-key",
        "GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test",
        "MONITORED_INBOXES": "info@test.com",
    })
    def test_command_creates_scheduler_jobs(
        self, mock_config, mock_state, mock_chat, mock_ai, mock_gmail, mock_scheduler_cls
    ):
        """Verify add_job is called 3 times: heartbeat, poll, retry."""
        from apps.emails.management.commands.run_scheduler import Command

        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_config.get.return_value = 5

        cmd = Command()
        # Scheduler.start() will block -- raise to exit
        mock_scheduler.start.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            cmd.handle()

        # Should have 3 add_job calls: heartbeat, poll, retry
        assert mock_scheduler.add_job.call_count == 3

    @pytest.mark.django_db
    def test_heartbeat_writes_to_system_config(self):
        """Call heartbeat function directly, verify SystemConfig updated."""
        from apps.emails.management.commands.run_scheduler import _heartbeat_job
        from apps.core.models import SystemConfig

        _heartbeat_job()

        val = SystemConfig.get("scheduler_heartbeat")
        assert val is not None
        assert len(val) > 10  # ISO timestamp

    @patch("apps.emails.management.commands.run_scheduler.signal.signal")
    @patch("apps.emails.management.commands.run_scheduler.BlockingScheduler")
    @patch("apps.emails.management.commands.run_scheduler.GmailPoller")
    @patch("apps.emails.management.commands.run_scheduler.AIProcessor")
    @patch("apps.emails.management.commands.run_scheduler.ChatNotifier")
    @patch("apps.emails.management.commands.run_scheduler.StateManager")
    @patch("apps.emails.management.commands.run_scheduler.SystemConfig")
    @patch.dict("os.environ", {
        "GOOGLE_SERVICE_ACCOUNT_KEY_PATH": "/app/secrets/sa.json",
        "ANTHROPIC_API_KEY": "test-key",
        "GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test",
        "MONITORED_INBOXES": "info@test.com",
    })
    def test_signal_handlers_registered(
        self, mock_config, mock_state, mock_chat, mock_ai, mock_gmail,
        mock_scheduler_cls, mock_signal
    ):
        """Verify SIGTERM and SIGINT handlers are registered."""
        from apps.emails.management.commands.run_scheduler import Command

        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_config.get.return_value = 5
        mock_scheduler.start.side_effect = KeyboardInterrupt

        cmd = Command()
        with pytest.raises(KeyboardInterrupt):
            cmd.handle()

        # Check signal handlers were registered
        signal_calls = [c[0][0] for c in mock_signal.call_args_list]
        assert signal.SIGTERM in signal_calls
        assert signal.SIGINT in signal_calls
