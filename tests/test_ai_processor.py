"""
Tests for the AI Processor module.

Tests email triage accuracy by running sample emails through Claude
and verifying category/priority assignments match expectations.

Usage:
    pytest tests/test_ai_processor.py -v
    pytest tests/test_ai_processor.py -v -k "test_triage_government"

Note: These tests make real Claude API calls and require ANTHROPIC_API_KEY.
For CI, mock the API calls or skip with: pytest -m "not integration"
"""

import json
import os
import sys
import pytest
from dataclasses import dataclass, field
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.ai_processor import AIProcessor, TriageResult, VALID_CATEGORIES, VALID_PRIORITIES


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

@dataclass
class MockEmail:
    """Minimal email object for testing."""
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


def load_sample_emails():
    """Load test emails from the sample_emails.json fixture."""
    fixture_path = os.path.join(os.path.dirname(__file__), "sample_emails.json")
    with open(fixture_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ai_processor():
    """Create an AI processor instance (requires ANTHROPIC_API_KEY)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping integration tests")

    return AIProcessor(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        temperature=0.3,
        system_prompt_path="prompts/triage_prompt.txt",
    )


# ----------------------------------------------------------------
# Unit Tests (no API calls)
# ----------------------------------------------------------------

class TestTriageResultDefaults:
    """Test TriageResult fallback/default behavior."""

    def test_default_values(self):
        result = TriageResult()
        assert result.category == "General Inquiry"
        assert result.priority == "MEDIUM"
        assert result.success is True
        assert result.error is None

    def test_fallback_result(self):
        result = AIProcessor._fallback_result("API timeout")
        assert result.success is False
        assert result.error == "API timeout"
        assert result.category == "General Inquiry"
        assert result.priority == "MEDIUM"
        assert "manual triage" in result.summary.lower()
        assert "needs-manual-triage" in result.tags


class TestInputValidation:
    """Test that valid categories and priorities are defined correctly."""

    def test_valid_categories(self):
        expected = [
            "Government/Tender", "Sales Lead", "Support Request", "Complaint",
            "Partnership", "Vendor", "Internal", "General Inquiry",
        ]
        assert VALID_CATEGORIES == expected

    def test_valid_priorities(self):
        assert VALID_PRIORITIES == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


class TestMessageBuilding:
    """Test the user message construction."""

    def test_basic_message(self):
        email = MockEmail(
            sender_name="John Doe",
            sender_email="john@test.com",
            subject="Hello World",
            body="This is a test email.",
        )
        processor = type("P", (), {"_build_user_message": AIProcessor._build_user_message})()
        msg = AIProcessor._build_user_message(processor, email)

        assert "John Doe" in msg
        assert "john@test.com" in msg
        assert "Hello World" in msg
        assert "This is a test email." in msg
        assert "info@vidarbhainfotech.com" in msg

    def test_message_with_attachments(self):
        email = MockEmail(
            attachment_count=2,
            attachment_names=["document.pdf", "image.png"],
        )
        processor = type("P", (), {"_build_user_message": AIProcessor._build_user_message})()
        msg = AIProcessor._build_user_message(processor, email)

        assert "Attachments (2)" in msg
        assert "document.pdf" in msg
        assert "image.png" in msg


# ----------------------------------------------------------------
# Integration Tests (require API key)
# ----------------------------------------------------------------

@pytest.mark.integration
class TestTriageAccuracy:
    """Test AI triage accuracy against sample emails."""

    def _run_triage(self, ai_processor, sample_email):
        """Helper to create a MockEmail from sample data and triage it."""
        email = MockEmail(
            inbox=sample_email["inbox"],
            sender_name=sample_email["from_name"],
            sender_email=sample_email["from_email"],
            subject=sample_email["subject"],
            body=sample_email["body"],
        )
        return ai_processor.process(email)

    def test_triage_government_tender(self, ai_processor):
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_001")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category == "Government/Tender"
        assert result.priority == "CRITICAL"
        assert len(result.summary) > 20
        assert len(result.draft_reply) > 50

    def test_triage_complaint(self, ai_processor):
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_002")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category in ("Complaint", "Support Request")
        assert result.priority in ("CRITICAL", "HIGH")

    def test_triage_sales_lead(self, ai_processor):
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_003")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category == "Sales Lead"
        assert result.priority in ("HIGH", "CRITICAL")

    def test_triage_vendor_invoice(self, ai_processor):
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_004")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category == "Vendor"
        assert result.priority == "LOW"

    def test_triage_newsletter(self, ai_processor):
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_007")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category == "General Inquiry"
        assert result.priority == "LOW"

    def test_triage_drdo_critical(self, ai_processor):
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_008")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category == "Government/Tender"
        assert result.priority == "CRITICAL"

    def test_triage_empty_body(self, ai_processor):
        """Edge case: email with no body."""
        samples = load_sample_emails()
        sample = next(s for s in samples if s["id"] == "test_009")
        result = self._run_triage(ai_processor, sample)

        assert result.success is True
        assert result.category in VALID_CATEGORIES
        assert result.priority in VALID_PRIORITIES

    def test_all_results_have_required_fields(self, ai_processor):
        """Verify all sample emails produce complete structured output."""
        samples = load_sample_emails()
        for sample in samples[:5]:  # Test first 5 to keep API costs reasonable
            result = self._run_triage(ai_processor, sample)
            assert result.category in VALID_CATEGORIES, f"Invalid category for {sample['id']}"
            assert result.priority in VALID_PRIORITIES, f"Invalid priority for {sample['id']}"
            assert isinstance(result.tags, list), f"Tags should be list for {sample['id']}"
