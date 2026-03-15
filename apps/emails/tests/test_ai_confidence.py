"""Tests for AI confidence tier in triage pipeline and template filters."""

import pytest
from unittest.mock import MagicMock, patch

from apps.emails.services.dtos import TriageResult
from apps.emails.services.ai_processor import TRIAGE_TOOL


# ---------------------------------------------------------------------------
# TriageResult DTO tests
# ---------------------------------------------------------------------------


class TestTriageResultConfidence:
    """Confidence field on TriageResult DTO."""

    def test_default_confidence_is_empty_string(self):
        result = TriageResult()
        assert result.confidence == ""

    def test_explicit_confidence_stored(self):
        result = TriageResult(confidence="HIGH")
        assert result.confidence == "HIGH"

    def test_confidence_medium(self):
        result = TriageResult(confidence="MEDIUM")
        assert result.confidence == "MEDIUM"

    def test_confidence_low(self):
        result = TriageResult(confidence="LOW")
        assert result.confidence == "LOW"


# ---------------------------------------------------------------------------
# TRIAGE_TOOL schema tests
# ---------------------------------------------------------------------------


class TestTriageToolConfidence:
    """Confidence field in TRIAGE_TOOL schema."""

    def test_confidence_in_properties(self):
        props = TRIAGE_TOOL["input_schema"]["properties"]
        assert "confidence" in props

    def test_confidence_is_enum(self):
        props = TRIAGE_TOOL["input_schema"]["properties"]
        assert props["confidence"]["type"] == "string"
        assert set(props["confidence"]["enum"]) == {"HIGH", "MEDIUM", "LOW"}

    def test_confidence_is_required(self):
        required = TRIAGE_TOOL["input_schema"]["required"]
        assert "confidence" in required


# ---------------------------------------------------------------------------
# AI Processor parsing tests
# ---------------------------------------------------------------------------


class TestAIProcessorConfidenceParsing:
    """_call_claude extracts confidence from Claude tool response."""

    @patch("apps.emails.services.ai_processor.anthropic.Anthropic")
    def test_parse_confidence_from_tool_result(self, mock_anthropic_cls):
        from apps.emails.services.ai_processor import AIProcessor

        # Build a mock response with tool_use block including confidence
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "triage_email"
        tool_block.input = {
            "category": "Sales Lead",
            "priority": "HIGH",
            "summary": "Test summary",
            "reasoning": "Test reasoning",
            "tags": ["test"],
            "language": "English",
            "confidence": "HIGH",
            "suggested_assignee": {"name": "", "reason": ""},
        }

        mock_response = MagicMock()
        mock_response.content = [tool_block]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.usage.cache_read_input_tokens = 0

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        processor = AIProcessor(anthropic_api_key="test-key")
        result = processor._call_claude("test message", "claude-haiku-4-5-20251001", 512)

        assert result.confidence == "HIGH"


# ---------------------------------------------------------------------------
# Pipeline save_email_to_db tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPipelineSaveConfidence:
    """save_email_to_db stores triage.confidence in Email.ai_confidence."""

    def test_save_confidence_to_email(self):
        from apps.emails.services.dtos import EmailMessage
        from apps.emails.services.pipeline import save_email_to_db
        from datetime import datetime, timezone

        email_msg = EmailMessage(
            thread_id="thread_conf_1",
            message_id="msg_conf_1",
            inbox="info@vidarbhainfotech.com",
            sender_name="Test",
            sender_email="test@example.com",
            subject="Confidence test",
            body="Body",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        triage = TriageResult(
            category="Sales Lead",
            priority="HIGH",
            summary="Test",
            reasoning="Test",
            confidence="MEDIUM",
        )

        email_obj = save_email_to_db(email_msg, triage)
        assert email_obj.ai_confidence == "MEDIUM"

    def test_spam_filtered_empty_confidence(self):
        """Spam-filtered emails have confidence='' and don't crash."""
        from apps.emails.services.dtos import EmailMessage
        from apps.emails.services.pipeline import save_email_to_db
        from datetime import datetime, timezone

        email_msg = EmailMessage(
            thread_id="thread_spam_1",
            message_id="msg_spam_1",
            inbox="info@vidarbhainfotech.com",
            sender_name="Spammer",
            sender_email="spam@example.com",
            subject="Buy now",
            body="Spam body",
            timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        triage = TriageResult(
            is_spam=True,
            spam_score=0.9,
            confidence="",
        )

        email_obj = save_email_to_db(email_msg, triage)
        assert email_obj.ai_confidence == ""


# ---------------------------------------------------------------------------
# update_thread_preview tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdateThreadPreviewConfidence:
    """update_thread_preview copies ai_confidence from latest triaged email to thread."""

    def test_copies_ai_confidence_to_thread(self):
        from apps.emails.models import Email, Thread
        from apps.emails.services.assignment import update_thread_preview
        from django.utils import timezone as tz

        thread = Thread.objects.create(
            gmail_thread_id="thread_preview_conf",
            subject="Preview confidence test",
        )
        Email.objects.create(
            message_id="msg_preview_conf_1",
            gmail_id="msg_preview_conf_1",
            gmail_thread_id="thread_preview_conf",
            thread=thread,
            from_address="test@example.com",
            from_name="Test",
            to_inbox="info@vidarbhainfotech.com",
            subject="Preview confidence test",
            body="Body",
            received_at=tz.now(),
            processing_status=Email.ProcessingStatus.COMPLETED,
            category="Sales Lead",
            priority="HIGH",
            ai_summary="Test summary",
            ai_confidence="HIGH",
        )

        update_thread_preview(thread)
        thread.refresh_from_db()
        assert thread.ai_confidence == "HIGH"


# ---------------------------------------------------------------------------
# Template filter tests
# ---------------------------------------------------------------------------


class TestConfidenceTemplateFilters:
    """confidence_base and confidence_tooltip template filters."""

    def test_confidence_base_high(self):
        from apps.emails.templatetags.email_tags import confidence_base
        assert confidence_base("HIGH") == "emerald"

    def test_confidence_base_medium(self):
        from apps.emails.templatetags.email_tags import confidence_base
        assert confidence_base("MEDIUM") == "amber"

    def test_confidence_base_low(self):
        from apps.emails.templatetags.email_tags import confidence_base
        assert confidence_base("LOW") == "red"

    def test_confidence_base_empty(self):
        from apps.emails.templatetags.email_tags import confidence_base
        assert confidence_base("") == "slate"

    def test_confidence_tooltip_high(self):
        from apps.emails.templatetags.email_tags import confidence_tooltip
        assert "highly confident" in confidence_tooltip("HIGH")

    def test_confidence_tooltip_medium(self):
        from apps.emails.templatetags.email_tags import confidence_tooltip
        assert "moderate" in confidence_tooltip("MEDIUM")

    def test_confidence_tooltip_low(self):
        from apps.emails.templatetags.email_tags import confidence_tooltip
        assert "uncertain" in confidence_tooltip("LOW")

    def test_confidence_tooltip_empty(self):
        from apps.emails.templatetags.email_tags import confidence_tooltip
        assert confidence_tooltip("") == ""
