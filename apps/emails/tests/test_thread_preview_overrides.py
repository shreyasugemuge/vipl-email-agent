"""Tests for override guards in update_thread_preview (07-01).

Ensures that user-corrected category/priority (flagged via category_overridden
and priority_overridden) are NOT overwritten when update_thread_preview runs
after a new email arrives in the thread.
"""

import pytest
from django.utils import timezone

from apps.emails.models import Email, Thread
from apps.emails.services.assignment import update_thread_preview


@pytest.fixture
def thread_with_email(db):
    """Create a thread with one COMPLETED email."""
    thread = Thread.objects.create(
        gmail_thread_id="thread-override-1",
        subject="Original subject",
        category="billing",
        priority="HIGH",
        ai_summary="Old summary",
        ai_draft_reply="Old draft",
        ai_confidence="MEDIUM",
    )
    Email.objects.create(
        thread=thread,
        message_id="msg-override-1",
        subject="Original subject",
        from_name="Alice",
        from_address="alice@example.com",
        body="Hello",
        received_at=timezone.now(),
        processing_status=Email.ProcessingStatus.COMPLETED,
        category="support",
        priority="LOW",
        ai_summary="New AI summary",
        ai_draft_reply="New AI draft",
        ai_confidence="HIGH",
    )
    return thread


@pytest.mark.django_db
class TestOverrideGuards:
    """update_thread_preview must respect override flags."""

    def test_category_overridden_preserved(self, thread_with_email):
        """Thread with category_overridden=True keeps its category."""
        thread = thread_with_email
        thread.category_overridden = True
        thread.save(update_fields=["category_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        # Category should stay "billing" (user's correction), NOT "support" (AI)
        assert thread.category == "billing"

    def test_priority_overridden_preserved(self, thread_with_email):
        """Thread with priority_overridden=True keeps its priority."""
        thread = thread_with_email
        thread.priority_overridden = True
        thread.save(update_fields=["priority_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        # Priority should stay "HIGH" (user's correction), NOT "LOW" (AI)
        assert thread.priority == "HIGH"

    def test_no_overrides_updates_both(self, thread_with_email):
        """Thread with both flags False gets category and priority from latest email."""
        thread = thread_with_email

        update_thread_preview(thread)
        thread.refresh_from_db()

        # Both should be updated from the email's triage
        assert thread.category == "support"
        assert thread.priority == "LOW"

    def test_category_overridden_still_updates_ai_fields(self, thread_with_email):
        """Even with category_overridden, ai_summary/draft/confidence still update."""
        thread = thread_with_email
        thread.category_overridden = True
        thread.save(update_fields=["category_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.ai_summary == "New AI summary"
        assert thread.ai_draft_reply == "New AI draft"
        assert thread.ai_confidence == "HIGH"

    def test_both_overridden_still_updates_preview_fields(self, thread_with_email):
        """Even with both overrides, last_message_at/last_sender/subject update."""
        thread = thread_with_email
        thread.category_overridden = True
        thread.priority_overridden = True
        thread.save(update_fields=["category_overridden", "priority_overridden"])

        update_thread_preview(thread)
        thread.refresh_from_db()

        assert thread.last_sender == "Alice"
        assert thread.last_sender_address == "alice@example.com"
        assert thread.subject == "Original subject"
