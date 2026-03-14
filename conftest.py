"""Shared test fixtures for VIPL Email Agent v2."""

import pytest
from datetime import datetime, timezone
from django.test import Client


@pytest.fixture
def admin_user(db):
    """Create an admin user (role=admin, is_staff=True)."""
    from apps.accounts.models import User

    return User.objects.create_user(
        username="admin",
        password="testpass123",
        email="admin@vidarbhainfotech.com",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def member_user(db):
    """Create a team member user (role=member)."""
    from apps.accounts.models import User

    return User.objects.create_user(
        username="member",
        password="testpass123",
        email="member@vidarbhainfotech.com",
        role=User.Role.MEMBER,
    )


@pytest.fixture
def client():
    """Django test client."""
    return Client()


def make_email_message(**overrides):
    """Factory for EmailMessage DTOs with sensible defaults."""
    from apps.emails.services.dtos import EmailMessage

    defaults = {
        "thread_id": "thread_abc123",
        "message_id": "msg_abc123",
        "inbox": "info@vidarbhainfotech.com",
        "sender_name": "Test Sender",
        "sender_email": "sender@example.com",
        "subject": "Test Email Subject",
        "body": "This is a test email body for unit testing.",
        "timestamp": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        "attachment_count": 0,
        "attachment_names": [],
        "attachment_details": [],
        "gmail_link": "https://mail.google.com/mail/u/?authuser=info@vidarbhainfotech.com#inbox/thread_abc123",
    }
    defaults.update(overrides)
    return EmailMessage(**defaults)


def make_triage_result(**overrides):
    """Factory for TriageResult DTOs with sensible defaults."""
    from apps.emails.services.dtos import TriageResult

    defaults = {
        "category": "General Inquiry",
        "priority": "MEDIUM",
        "summary": "Test email summary for unit testing.",
        "reasoning": "Standard test email.",
        "language": "English",
        "tags": ["test"],
        "suggested_assignee": "",
        "model_used": "claude-haiku-4-5-20251001",
        "input_tokens": 100,
        "output_tokens": 50,
        "is_spam": False,
        "spam_score": 0.0,
    }
    defaults.update(overrides)
    return TriageResult(**defaults)
