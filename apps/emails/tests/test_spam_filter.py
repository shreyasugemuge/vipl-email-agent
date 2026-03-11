"""Tests for spam filter service."""

import pytest
from datetime import datetime, timezone

from apps.emails.services.dtos import EmailMessage, TriageResult
from apps.emails.services.spam_filter import is_spam, SPAM_PATTERNS


class TestSpamFilter:
    """Test spam regex pre-filter."""

    def _make_email(self, subject="", body=""):
        return EmailMessage(
            thread_id="t1",
            message_id="m1",
            inbox="info@vidarbhainfotech.com",
            sender_name="Test",
            sender_email="test@example.com",
            subject=subject,
            body=body,
            timestamp=datetime.now(tz=timezone.utc),
        )

    def test_spam_detected_unsubscribe(self):
        email = self._make_email(body="Click here to unsubscribe from this list")
        result = is_spam(email)
        assert result is not None
        assert result.is_spam is True

    def test_spam_detected_lottery(self):
        email = self._make_email(subject="Congratulations lottery winner!")
        result = is_spam(email)
        assert result is not None
        assert result.is_spam is True

    def test_spam_detected_account_suspended(self):
        email = self._make_email(subject="Your account has been suspended")
        result = is_spam(email)
        assert result is not None
        assert result.is_spam is True

    def test_spam_detected_earn_money(self):
        email = self._make_email(body="Earn $5000 per day working from home")
        result = is_spam(email)
        assert result is not None
        assert result.is_spam is True

    def test_clean_email_returns_none(self):
        email = self._make_email(
            subject="Tender submission for GST project",
            body="Please find attached the requirements for the upcoming tender.",
        )
        result = is_spam(email)
        assert result is None

    def test_spam_result_has_correct_fields(self):
        email = self._make_email(subject="You have been selected for a prize!")
        result = is_spam(email)
        assert result is not None
        assert result.category == "Spam"
        assert result.is_spam is True
        assert result.priority == "LOW"
        assert result.model_used == "spam-filter"

    def test_spam_check_case_insensitive(self):
        email = self._make_email(subject="CLICK HERE TO OPT OUT now")
        result = is_spam(email)
        assert result is not None
        assert result.is_spam is True

    def test_has_13_patterns(self):
        assert len(SPAM_PATTERNS) == 13
