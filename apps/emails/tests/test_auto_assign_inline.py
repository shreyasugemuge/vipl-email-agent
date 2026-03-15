"""Tests for inline auto-assign in pipeline (02-02).

Tests the is_auto_assigned field and the _try_inline_auto_assign function
that runs during process_single_email for HIGH confidence threads.
"""

import pytest
from django.utils import timezone

from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    AssignmentRule,
    Email,
    Thread,
)


@pytest.mark.django_db
class TestIsAutoAssignedField:
    """Test Thread.is_auto_assigned model field."""

    def test_defaults_to_false(self):
        thread = Thread(gmail_thread_id="t1", subject="Test")
        assert thread.is_auto_assigned is False

    def test_can_be_set_to_true(self):
        thread = Thread.objects.create(gmail_thread_id="t2", subject="Test")
        thread.is_auto_assigned = True
        thread.save()
        thread.refresh_from_db()
        assert thread.is_auto_assigned is True
