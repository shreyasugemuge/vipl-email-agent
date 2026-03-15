"""Tests for the distillation service -- AssignmentFeedback -> compact AI rules."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import SystemConfig
from apps.emails.models import AssignmentFeedback, Thread

User = get_user_model()


@pytest.fixture
def team_users(db):
    """Create two team members for feedback scenarios."""
    rahul = User.objects.create_user(
        username="rahul",
        email="rahul@vidarbhainfotech.com",
        password="test1234",
        first_name="Rahul",
        last_name="Sharma",
    )
    priya = User.objects.create_user(
        username="priya",
        email="priya@vidarbhainfotech.com",
        password="test1234",
        first_name="Priya",
        last_name="Patil",
    )
    return rahul, priya


@pytest.fixture
def thread_with_feedback(db, team_users):
    """Create a thread with rejected feedback."""
    rahul, priya = team_users
    thread = Thread.objects.create(
        gmail_thread_id="thread_distill_001",
        subject="STPI tender submission deadline",
        category="Government/Tender",
        priority="HIGH",
        last_sender_address="govt@stpi.in",
    )
    AssignmentFeedback.objects.create(
        thread=thread,
        suggested_user=rahul,
        actual_user=priya,
        action=AssignmentFeedback.FeedbackAction.REASSIGNED,
        confidence_at_time="HIGH",
        user_who_acted=priya,
    )
    return thread


# ----------------------------------------------------------------
# distill_correction_rules() -- no feedback
# ----------------------------------------------------------------

class TestDistillNoFeedback:
    @patch("apps.emails.services.distillation._call_haiku_distill")
    def test_no_feedback_no_api_call(self, mock_haiku, db):
        """No feedback at all -> no-op, no Haiku call."""
        from apps.emails.services.distillation import distill_correction_rules

        distill_correction_rules()
        mock_haiku.assert_not_called()

    @patch("apps.emails.services.distillation._call_haiku_distill")
    def test_only_accepted_feedback_no_api_call(self, mock_haiku, db, team_users):
        """Only accepted feedback -> no-op (we only learn from corrections)."""
        rahul, priya = team_users
        thread = Thread.objects.create(
            gmail_thread_id="thread_accepted_001",
            subject="Some email",
            category="General Inquiry",
            last_sender_address="someone@example.com",
        )
        AssignmentFeedback.objects.create(
            thread=thread,
            suggested_user=rahul,
            actual_user=rahul,
            action=AssignmentFeedback.FeedbackAction.ACCEPTED,
            user_who_acted=priya,
        )
        from apps.emails.services.distillation import distill_correction_rules

        distill_correction_rules()
        mock_haiku.assert_not_called()


# ----------------------------------------------------------------
# distill_correction_rules() -- with rejected feedback
# ----------------------------------------------------------------

class TestDistillWithFeedback:
    @patch("apps.emails.services.distillation._call_haiku_distill")
    def test_rejected_feedback_calls_haiku(self, mock_haiku, db, thread_with_feedback):
        """Rejected feedback triggers Haiku call and stores rules."""
        mock_haiku.return_value = "- Government/Tender emails about STPI: assign to Priya"

        from apps.emails.services.distillation import distill_correction_rules

        distill_correction_rules()
        mock_haiku.assert_called_once()

        # Rules stored in SystemConfig
        rules = SystemConfig.get("correction_rules", "")
        assert "Priya" in rules
        assert "STPI" in rules

    @patch("apps.emails.services.distillation._call_haiku_distill")
    def test_last_distillation_epoch_updated(self, mock_haiku, db, thread_with_feedback):
        """Successful distillation updates last_distillation_epoch."""
        mock_haiku.return_value = "- Some rule"

        from apps.emails.services.distillation import distill_correction_rules

        before = int(timezone.now().timestamp())
        distill_correction_rules()

        epoch = SystemConfig.get("last_distillation_epoch", 0)
        assert int(epoch) >= before


# ----------------------------------------------------------------
# Skips when no new feedback since last distillation
# ----------------------------------------------------------------

class TestDistillSkipsStale:
    @patch("apps.emails.services.distillation._call_haiku_distill")
    def test_skips_when_no_new_feedback(self, mock_haiku, db, thread_with_feedback):
        """If last_distillation_epoch is after all feedback, skip."""
        # Set epoch to future (no new feedback)
        future_epoch = str(int(timezone.now().timestamp()) + 3600)
        SystemConfig.objects.update_or_create(
            key="last_distillation_epoch",
            defaults={"value": future_epoch, "value_type": "int"},
        )

        from apps.emails.services.distillation import distill_correction_rules

        distill_correction_rules()
        mock_haiku.assert_not_called()


# ----------------------------------------------------------------
# Handles API failure gracefully
# ----------------------------------------------------------------

class TestDistillFailureHandling:
    @patch("apps.emails.services.distillation._do_distill", side_effect=Exception("API down"))
    def test_api_failure_does_not_crash(self, mock_distill, db):
        """Distillation failure is swallowed, never crashes pipeline."""
        from apps.emails.services.distillation import distill_correction_rules

        # Should not raise
        distill_correction_rules()

    @patch("apps.emails.services.distillation._call_haiku_distill", return_value=None)
    def test_haiku_returns_none_no_crash(self, mock_haiku, db, thread_with_feedback):
        """If Haiku returns None, no rules stored, no crash."""
        from apps.emails.services.distillation import distill_correction_rules

        distill_correction_rules()
        rules = SystemConfig.get("correction_rules", "")
        assert rules == ""


# ----------------------------------------------------------------
# _format_corrections
# ----------------------------------------------------------------

class TestFormatCorrections:
    def test_format_corrections_output(self, db, thread_with_feedback, team_users):
        """Format produces readable text with category, subject, sender, and people."""
        from apps.emails.services.distillation import _format_corrections

        feedbacks = AssignmentFeedback.objects.filter(
            action__in=["rejected", "reassigned"]
        ).select_related("thread", "suggested_user", "actual_user")

        text = _format_corrections(feedbacks)
        assert "Government/Tender" in text
        assert "STPI" in text
        assert "Rahul" in text
        assert "Priya" in text
        assert "govt@stpi.in" in text


# ----------------------------------------------------------------
# Rules stored correctly in SystemConfig
# ----------------------------------------------------------------

class TestRulesStorage:
    @patch("apps.emails.services.distillation._call_haiku_distill")
    def test_rules_stored_as_str_type(self, mock_haiku, db, thread_with_feedback):
        """Correction rules stored with value_type STR in SystemConfig."""
        mock_haiku.return_value = "- Sales leads from acme.com: assign to Rahul"

        from apps.emails.services.distillation import distill_correction_rules

        distill_correction_rules()

        config = SystemConfig.objects.get(key="correction_rules")
        assert config.value_type == "str"
        assert config.category == "ai"
        assert "Rahul" in config.value


# ----------------------------------------------------------------
# AI Processor prompt injection
# ----------------------------------------------------------------

class TestAIProcessorPromptInjection:
    """Test that correction rules from SystemConfig are injected into the AI system prompt."""

    def test_correction_rules_in_prompt(self, db):
        """When correction_rules exist in SystemConfig, they appear in the system prompt."""
        SystemConfig.objects.update_or_create(
            key="correction_rules",
            defaults={
                "value": "- STPI emails: assign to Priya\n- Sales leads: assign to Rahul",
                "value_type": "str",
                "category": "ai",
            },
        )
        # Clear cache so AIProcessor picks up the new value
        SystemConfig.invalidate_cache()

        from apps.emails.services.ai_processor import AIProcessor

        processor = AIProcessor(anthropic_api_key="test-key-fake")
        prompt_text = processor.system_prompt[0]["text"]

        assert "<correction_rules>" in prompt_text
        assert "STPI emails: assign to Priya" in prompt_text
        assert "Sales leads: assign to Rahul" in prompt_text
        assert "</correction_rules>" in prompt_text

    def test_no_correction_rules_no_block(self, db):
        """When correction_rules is empty, no <correction_rules> block in prompt."""
        # Ensure no correction_rules key exists
        SystemConfig.objects.filter(key="correction_rules").delete()
        SystemConfig.invalidate_cache()

        from apps.emails.services.ai_processor import AIProcessor

        processor = AIProcessor(anthropic_api_key="test-key-fake")
        prompt_text = processor.system_prompt[0]["text"]

        assert "<correction_rules>" not in prompt_text

    def test_no_correction_rules_placeholder_excluded(self, db):
        """When correction_rules is 'No correction rules yet.', no block injected."""
        SystemConfig.objects.update_or_create(
            key="correction_rules",
            defaults={
                "value": "No correction rules yet.",
                "value_type": "str",
                "category": "ai",
            },
        )
        SystemConfig.invalidate_cache()

        from apps.emails.services.ai_processor import AIProcessor

        processor = AIProcessor(anthropic_api_key="test-key-fake")
        prompt_text = processor.system_prompt[0]["text"]

        assert "<correction_rules>" not in prompt_text

    def test_cache_control_still_applied(self, db):
        """Prompt cache_control is still present after rules injection."""
        SystemConfig.objects.update_or_create(
            key="correction_rules",
            defaults={"value": "- Some rule", "value_type": "str", "category": "ai"},
        )
        SystemConfig.invalidate_cache()

        from apps.emails.services.ai_processor import AIProcessor

        processor = AIProcessor(anthropic_api_key="test-key-fake")
        assert processor.system_prompt[0]["cache_control"] == {"type": "ephemeral"}
