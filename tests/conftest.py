"""Shared pytest fixtures for all VIPL Email Agent tests."""

import json
import os

import pytest
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import MagicMock


@dataclass
class MockEmail:
    """Minimal email object matching the EmailMessage interface."""
    thread_id: str = "test_thread"
    message_id: str = "test_msg"
    inbox: str = "info@vidarbhainfotech.com"
    sender_name: str = "Test Sender"
    sender_email: str = "test@example.com"
    subject: str = "Test Subject"
    body: str = "Test body content"
    timestamp: datetime = None
    attachment_count: int = 0
    attachment_names: list = field(default_factory=list)
    gmail_link: str = ""

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@pytest.fixture
def mock_email():
    return MockEmail()


@pytest.fixture
def sample_emails():
    path = os.path.join(os.path.dirname(__file__), "sample_emails.json")
    with open(path, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_sheet():
    """Mock SheetLogger with sensible defaults."""
    sheet = MagicMock()
    sheet.get_open_tickets.return_value = []
    sheet.get_all_tickets.return_value = []
    sheet.get_all_tickets_today.return_value = []
    sheet.get_sla_config.return_value = {}
    sheet.is_thread_logged.return_value = False
    sheet.log_email.return_value = "INF-0001"
    sheet.spreadsheet_id = "test-sheet-id"
    sheet.sheets = MagicMock()
    return sheet


@pytest.fixture
def mock_chat():
    """Mock ChatNotifier."""
    chat = MagicMock()
    chat.notify_poll_summary.return_value = True
    chat.notify_sla_breach.return_value = True
    chat.notify_sla_summary.return_value = True
    chat.notify_eod_summary.return_value = True
    chat.notify_startup.return_value = True
    return chat


@pytest.fixture
def default_config():
    """Minimal config dict for testing."""
    return {
        "gmail": {
            "inboxes": ["info@vidarbhainfotech.com"],
            "poll_interval_seconds": 300,
            "processed_label": "Agent/Processed",
        },
        "claude": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 512,
            "temperature": 0.3,
        },
        "google_sheets": {
            "spreadsheet_id": "test-sheet-id",
            "email_log_tab": "Email Log",
            "sla_config_tab": "SLA Config",
            "team_tab": "Team",
            "agent_config_tab": "Agent Config",
        },
        "google_chat": {"webhook_url": "https://chat.googleapis.com/test"},
        "google": {"service_account_key_path": "/tmp/fake-sa.json"},
        "admin": {"email": "admin@test.com"},
        "eod": {
            "recipients": ["admin@test.com"],
            "send_hour": 19,
            "send_minute": 0,
            "timezone": "Asia/Kolkata",
        },
        "sla": {
            "business_hours_only": False,
            "business_hours_start": 9,
            "business_hours_end": 18,
            "business_days": [0, 1, 2, 3, 4, 5],
            "breach_alert_cooldown_hours": 4,
            "summary_hours": [9, 13, 17],
        },
        "quiet_hours": {"enabled": False},
        "feature_flags": {
            "ai_enabled": True,
            "chat_enabled": True,
            "eod_email_enabled": True,
        },
    }
