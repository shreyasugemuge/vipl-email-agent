"""Tests for AIProcessor service module.

All tests mock Anthropic API calls entirely -- no real network, no API key needed.
"""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from conftest import make_email_message


class TestCleanXmlTags:
    """Test _clean_xml_tags utility function."""

    def test_empty_string_returns_empty(self):
        from apps.emails.services.ai_processor import _clean_xml_tags
        assert _clean_xml_tags("") == ""

    def test_none_returns_none(self):
        from apps.emails.services.ai_processor import _clean_xml_tags
        assert _clean_xml_tags(None) is None

    def test_plain_name_unchanged(self):
        from apps.emails.services.ai_processor import _clean_xml_tags
        assert _clean_xml_tags("Shreyas") == "Shreyas"

    def test_strips_parameter_xml_tag(self):
        from apps.emails.services.ai_processor import _clean_xml_tags
        assert _clean_xml_tags('<parameter name="name">Shreyas</parameter>') == "Shreyas"

    def test_strips_parameter_xml_tag_with_unicode(self):
        from apps.emails.services.ai_processor import _clean_xml_tags
        result = _clean_xml_tags('<parameter name="name">Shreyas Uge</parameter>')
        assert result == "Shreyas Uge"

    def test_strips_generic_xml_tags(self):
        from apps.emails.services.ai_processor import _clean_xml_tags
        assert _clean_xml_tags("<foo>bar</foo>") == "bar"


class TestParseAssigneeXmlCleanup:
    """Test that _parse_suggested_assignee cleans XML from name values."""

    def test_dict_with_xml_name_cleaned(self):
        from apps.emails.services.ai_processor import _parse_suggested_assignee
        result = _parse_suggested_assignee({
            "name": '<parameter name="name">Shreyas</parameter>',
            "reason": "Good fit",
        })
        assert result == {"name": "Shreyas", "reason": "Good fit"}

    def test_string_with_xml_cleaned(self):
        from apps.emails.services.ai_processor import _parse_suggested_assignee
        result = _parse_suggested_assignee('<parameter name="name">Shreyas</parameter>')
        assert result == {"name": "Shreyas", "reason": ""}


class TestAIProcessor:
    """Test AIProcessor triage with mocked Claude API."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"})
    @patch("apps.emails.services.ai_processor.anthropic.Anthropic")
    def test_process_returns_triage_result(self, mock_anthropic_cls):
        from apps.emails.services.ai_processor import AIProcessor

        # Mock the Claude API response
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "triage_email"
        mock_tool_block.input = {
            "category": "Sales Lead",
            "priority": "HIGH",
            "summary": "A potential sales inquiry from a new client.",

            "reasoning": "Business inquiry with clear intent.",
            "suggested_assignee": "Sales Team",
            "tags": ["sales", "new-client"],
            "language": "English",
        }

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_usage = MagicMock()
        mock_usage.input_tokens = 200
        mock_usage.output_tokens = 100
        mock_usage.cache_read_input_tokens = 50
        mock_response.usage = mock_usage
        mock_client.messages.create.return_value = mock_response

        processor = AIProcessor(anthropic_api_key="test-key-123")
        email = make_email_message(subject="Interested in your services")
        result = processor.process(email)

        assert result.category == "Sales Lead"
        assert result.priority == "HIGH"
        assert result.language == "English"
        assert result.model_used == "claude-haiku-4-5-20251001"
        assert result.input_tokens == 200
        assert result.output_tokens == 100

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"})
    @patch("apps.emails.services.ai_processor.anthropic.Anthropic")
    def test_two_tier_uses_haiku_by_default(self, mock_anthropic_cls):
        from apps.emails.services.ai_processor import AIProcessor

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "triage_email"
        mock_tool_block.input = {
            "category": "General Inquiry",
            "priority": "MEDIUM",
            "summary": "A general inquiry.",

            "reasoning": "Routine email.",
            "suggested_assignee": "",
            "tags": ["general"],
            "language": "English",
        }

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.cache_read_input_tokens = 0
        mock_response.usage = mock_usage
        mock_client.messages.create.return_value = mock_response

        processor = AIProcessor(anthropic_api_key="test-key-123")
        email = make_email_message()
        processor.process(email)

        # Verify the model used in the API call is Haiku
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_fallback_result_safe_defaults(self):
        from apps.emails.services.ai_processor import AIProcessor

        result = AIProcessor._fallback_result("Test error")
        assert result.category == "General Inquiry"
        assert result.priority == "MEDIUM"
        assert result.model_used == "fallback"
        assert "AI processing failed" in result.summary

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"})
    @patch("apps.emails.services.ai_processor.anthropic.Anthropic")
    def test_body_truncation(self, mock_anthropic_cls):
        from apps.emails.services.ai_processor import AIProcessor

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "triage_email"
        mock_tool_block.input = {
            "category": "General Inquiry",
            "priority": "LOW",
            "summary": "Long email.",

            "reasoning": "Routine.",
            "suggested_assignee": "",
            "tags": [],
            "language": "English",
        }

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.cache_read_input_tokens = 0
        mock_response.usage = mock_usage
        mock_client.messages.create.return_value = mock_response

        processor = AIProcessor(anthropic_api_key="test-key-123")

        # Create email with body > 1500 chars
        long_body = "A" * 3000
        email = make_email_message(body=long_body)
        processor.process(email)

        # Verify the user message sent to Claude has truncated body
        call_args = mock_client.messages.create.call_args
        user_message = call_args.kwargs["messages"][0]["content"]
        # The body in the user message should be truncated to 1500 chars + truncation marker
        assert len(user_message) < 3000
        assert "[...truncated...]" in user_message

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"})
    @patch("apps.emails.services.ai_processor.anthropic.Anthropic")
    def test_input_sanitization(self, mock_anthropic_cls):
        from apps.emails.services.ai_processor import AIProcessor

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "triage_email"
        mock_tool_block.input = {
            "category": "General Inquiry",
            "priority": "LOW",
            "summary": "Test.",

            "reasoning": "Routine.",
            "suggested_assignee": "",
            "tags": [],
            "language": "English",
        }

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.cache_read_input_tokens = 0
        mock_response.usage = mock_usage
        mock_client.messages.create.return_value = mock_response

        processor = AIProcessor(anthropic_api_key="test-key-123")

        # Email with control characters in subject and body
        email = make_email_message(
            subject="Test\x00Subject\x01With\x02Controls",
            body="Body\x00with\x03null\x04bytes",
        )
        processor.process(email)

        # Verify control chars are stripped from the message sent to Claude
        call_args = mock_client.messages.create.call_args
        user_message = call_args.kwargs["messages"][0]["content"]
        assert "\x00" not in user_message
        assert "\x01" not in user_message
        assert "\x02" not in user_message
        assert "\x03" not in user_message
        assert "\x04" not in user_message
        # But normal text is preserved
        assert "Test" in user_message
        assert "Subject" in user_message
