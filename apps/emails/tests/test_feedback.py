"""Tests for thread-level accept/reject suggestion views and AssignmentFeedback recording."""

import json

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import (
    ActivityLog,
    AssignmentFeedback,
    Email,
    Thread,
)


class ThreadSuggestionViewTestBase(TestCase):
    """Shared setup for accept/reject thread suggestion tests."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@vidarbhainfotech.com",
            password="testpass123",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member",
            email="member@vidarbhainfotech.com",
            password="testpass123",
            role=User.Role.MEMBER,
        )
        self.suggested_user = User.objects.create_user(
            username="suggested",
            email="suggested@vidarbhainfotech.com",
            password="testpass123",
            first_name="Suggested",
            last_name="User",
        )

        self.thread = Thread.objects.create(
            subject="Test thread",
            status=Thread.Status.NEW,
            ai_confidence="HIGH",
        )
        self.email = Email.objects.create(
            thread=self.thread,
            message_id="<msg001@example.com>",
            gmail_id="msg001",
            subject="Test email",
            from_address="sender@example.com",
            to_inbox="info@vidarbhainfotech.com",
            received_at=timezone.now(),
            processing_status=Email.ProcessingStatus.COMPLETED,
            ai_suggested_assignee={
                "name": "Suggested User",
                "user_id": None,  # will be set in setUp
                "reason": "Best match",
            },
        )
        # Set the user_id after user creation
        self.email.ai_suggested_assignee["user_id"] = self.suggested_user.pk
        self.email.save(update_fields=["ai_suggested_assignee"])

        self.client = Client()


class AcceptThreadSuggestionTest(ThreadSuggestionViewTestBase):
    """Tests for accept_thread_suggestion view."""

    def test_accept_assigns_suggested_user_to_thread(self):
        """POST accept assigns the suggested user and clears auto flag."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.assigned_to, self.suggested_user)
        self.assertFalse(self.thread.is_auto_assigned)
        self.assertEqual(response.status_code, 200)

    def test_accept_creates_accepted_feedback(self):
        """Accept creates AssignmentFeedback with action=ACCEPTED."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        self.client.post(url)

        fb = AssignmentFeedback.objects.filter(
            thread=self.thread,
            action=AssignmentFeedback.FeedbackAction.ACCEPTED,
        ).first()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.suggested_user, self.suggested_user)
        self.assertEqual(fb.actual_user, self.suggested_user)
        self.assertEqual(fb.confidence_at_time, "HIGH")
        self.assertEqual(fb.user_who_acted, self.admin)

    def test_accept_creates_activity_log(self):
        """Accept creates an ActivityLog entry for assignment."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        self.client.post(url)

        log = ActivityLog.objects.filter(
            thread=self.thread,
            action=ActivityLog.Action.ASSIGNED,
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("Accepted AI suggestion", log.detail)

    def test_accept_returns_htmx_partial(self):
        """Accept returns rendered detail panel partial."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should contain thread detail content
        self.assertIn("Test thread", content)

    def test_accept_no_valid_suggestion_returns_error(self):
        """Accept with no valid suggestion returns 400-level error."""
        self.email.ai_suggested_assignee = {}
        self.email.save(update_fields=["ai_suggested_assignee"])

        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_accept(self):
        """Non-admin members get 403 on accept."""
        self.client.login(username="member", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_accept_auto_assigned_thread_clears_auto_flag(self):
        """Accepting on an auto-assigned thread clears is_auto_assigned."""
        self.thread.assigned_to = self.suggested_user
        self.thread.is_auto_assigned = True
        self.thread.save()

        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        self.client.post(url)

        self.thread.refresh_from_db()
        self.assertFalse(self.thread.is_auto_assigned)
        self.assertEqual(self.thread.assigned_to, self.suggested_user)


class RejectThreadSuggestionTest(ThreadSuggestionViewTestBase):
    """Tests for reject_thread_suggestion view."""

    def test_reject_unassigns_thread(self):
        """POST reject unassigns the thread."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.thread.refresh_from_db()
        self.assertIsNone(self.thread.assigned_to)
        self.assertFalse(self.thread.is_auto_assigned)
        self.assertEqual(response.status_code, 200)

    def test_reject_creates_rejected_feedback(self):
        """Reject creates AssignmentFeedback with action=REJECTED."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        self.client.post(url)

        fb = AssignmentFeedback.objects.filter(
            thread=self.thread,
            action=AssignmentFeedback.FeedbackAction.REJECTED,
        ).first()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.suggested_user, self.suggested_user)
        self.assertIsNone(fb.actual_user)
        self.assertEqual(fb.confidence_at_time, "HIGH")
        self.assertEqual(fb.user_who_acted, self.admin)

    def test_reject_auto_assigned_returns_to_unassigned(self):
        """Rejecting an auto-assigned thread returns it to Triage Queue (unassigned)."""
        self.thread.assigned_to = self.suggested_user
        self.thread.is_auto_assigned = True
        self.thread.save()

        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        self.client.post(url)

        self.thread.refresh_from_db()
        self.assertIsNone(self.thread.assigned_to)
        self.assertFalse(self.thread.is_auto_assigned)

    def test_reject_clears_ai_suggestion_on_email(self):
        """Reject clears ai_suggested_assignee on the latest email."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        self.client.post(url)

        self.email.refresh_from_db()
        self.assertEqual(self.email.ai_suggested_assignee, {})

    def test_reject_returns_htmx_partial(self):
        """Reject returns rendered detail panel partial."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Test thread", content)

    def test_non_admin_cannot_reject(self):
        """Non-admin members get 403 on reject."""
        self.client.login(username="member", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)


class AcceptSuggestionOOBSwapTest(ThreadSuggestionViewTestBase):
    """Tests that accept_thread_suggestion returns OOB card swap."""

    def test_accept_response_contains_oob_swap(self):
        """Accept returns HTML with hx-swap-oob for thread card update."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("hx-swap-oob", content)

    def test_accept_response_contains_thread_card(self):
        """Accept returns both detail panel and thread card HTML."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:accept_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        content = response.content.decode()
        # Detail panel content
        self.assertIn("Test thread", content)
        # OOB card should reference the thread id
        self.assertIn(f"thread-{self.thread.pk}", content)


class RejectSuggestionOOBSwapTest(ThreadSuggestionViewTestBase):
    """Tests that reject_thread_suggestion returns OOB card swap."""

    def test_reject_response_contains_oob_swap(self):
        """Reject returns HTML with hx-swap-oob for thread card update."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("hx-swap-oob", content)

    def test_reject_response_contains_thread_card(self):
        """Reject returns both detail panel and thread card HTML."""
        self.client.login(username="admin", password="testpass123")
        url = reverse("emails:reject_thread_suggestion", args=[self.thread.pk])
        response = self.client.post(url)

        content = response.content.decode()
        self.assertIn("Test thread", content)
        self.assertIn(f"thread-{self.thread.pk}", content)
