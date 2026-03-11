"""Tests for SystemConfig model."""

import pytest
from apps.core.models import SystemConfig


@pytest.mark.django_db
class TestSystemConfigGet:
    """Test SystemConfig.get() returns correctly typed values."""

    def test_get_string_value(self):
        SystemConfig.objects.create(key="test_str", value="hello", value_type="str")
        assert SystemConfig.get("test_str") == "hello"

    def test_get_int_value(self):
        SystemConfig.objects.create(key="test_int", value="42", value_type="int")
        assert SystemConfig.get("test_int") == 42

    def test_get_bool_value_true(self):
        SystemConfig.objects.create(key="test_bool", value="true", value_type="bool")
        assert SystemConfig.get("test_bool") is True

    def test_get_bool_value_false(self):
        SystemConfig.objects.create(key="test_bool_f", value="false", value_type="bool")
        assert SystemConfig.get("test_bool_f") is False

    def test_get_float_value(self):
        SystemConfig.objects.create(key="test_float", value="3.14", value_type="float")
        assert SystemConfig.get("test_float") == pytest.approx(3.14)

    def test_get_json_value(self):
        SystemConfig.objects.create(
            key="test_json", value='{"a": 1, "b": [2, 3]}', value_type="json"
        )
        result = SystemConfig.get("test_json")
        assert result == {"a": 1, "b": [2, 3]}

    def test_get_missing_key_returns_default(self):
        assert SystemConfig.get("nonexistent", "fallback") == "fallback"

    def test_get_missing_key_returns_none(self):
        assert SystemConfig.get("nonexistent") is None

    def test_typed_value_invalid_returns_raw(self):
        SystemConfig.objects.create(key="bad_int", value="not_a_number", value_type="int")
        # Should return raw string when cast fails
        assert SystemConfig.get("bad_int") == "not_a_number"


@pytest.mark.django_db
class TestSystemConfigGetAllByCategory:
    """Test SystemConfig.get_all_by_category() returns dict of typed values."""

    def test_get_all_by_category(self):
        SystemConfig.objects.create(
            key="flag_a", value="true", value_type="bool", category="test_category"
        )
        SystemConfig.objects.create(
            key="flag_b", value="false", value_type="bool", category="test_category"
        )
        SystemConfig.objects.create(
            key="other", value="123", value_type="int", category="other_category"
        )
        result = SystemConfig.get_all_by_category("test_category")
        assert result == {"flag_a": True, "flag_b": False}
        assert "other" not in result


@pytest.mark.django_db
class TestSystemConfigSeedData:
    """Test that data migration seeds expected entries."""

    def test_seed_data_exists(self):
        """Verify data migration created feature flags and polling config."""
        # Feature flags
        assert SystemConfig.get("ai_triage_enabled") is True
        assert SystemConfig.get("chat_notifications_enabled") is True
        assert SystemConfig.get("eod_email_enabled") is True

        # Polling config
        assert SystemConfig.get("poll_interval_minutes") == 5
        assert SystemConfig.get("max_consecutive_failures") == 3

        # Quiet hours
        assert SystemConfig.get("quiet_hours_start") == 20
        assert SystemConfig.get("quiet_hours_end") == 8

        # Business hours
        assert SystemConfig.get("business_hours_start") == 8
        assert SystemConfig.get("business_hours_end") == 21


@pytest.mark.django_db
class TestEmailModelNewFields:
    """Test Email model has all new Phase 2 fields."""

    def test_email_processing_status_choices(self):
        from apps.emails.models import Email

        choices = [c[0] for c in Email.ProcessingStatus.choices]
        assert "pending" in choices
        assert "processing" in choices
        assert "completed" in choices
        assert "failed" in choices
        assert "exhausted" in choices

    def test_email_has_new_fields(self):
        from apps.emails.models import Email
        from django.utils import timezone

        email = Email(
            message_id="test-123",
            from_address="test@example.com",
            to_inbox="info@vidarbhainfotech.com",
            received_at=timezone.now(),
            processing_status="pending",
            retry_count=0,
            last_error="",
            is_spam=False,
            language="English",
            ai_reasoning="test reasoning",
            ai_model_used="haiku",
            ai_tags=["test"],
            ai_suggested_assignee="someone",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/abc",
            ai_input_tokens=100,
            ai_output_tokens=50,
            body_html="<p>test</p>",
            spam_score=0.5,
        )
        assert email.processing_status == "pending"
        assert email.retry_count == 0
        assert email.is_spam is False
        assert email.language == "English"
        assert email.ai_reasoning == "test reasoning"
        assert email.ai_model_used == "haiku"
        assert email.ai_tags == ["test"]
        assert email.ai_suggested_assignee == "someone"
        assert email.gmail_link == "https://mail.google.com/mail/u/0/#inbox/abc"
        assert email.ai_input_tokens == 100
        assert email.ai_output_tokens == 50
        assert email.body_html == "<p>test</p>"
        assert email.spam_score == 0.5
