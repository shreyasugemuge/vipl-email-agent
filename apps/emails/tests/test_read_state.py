"""Tests for per-user read/unread tracking backend logic.

Covers: ThreadReadState upsert on detail open, mark-unread endpoint,
assignment read-state reset, and queryset unread annotation.
"""

import pytest
from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import Thread, ThreadReadState
from conftest import create_thread


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def thread(db):
    return create_thread(last_message_at=timezone.now() - timedelta(hours=1))


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other",
        password="testpass123",
        email="other@vidarbhainfotech.com",
        role=User.Role.MEMBER,
    )


# ---------------------------------------------------------------------------
# TestMarkAsRead -- opening thread_detail creates / updates ThreadReadState
# ---------------------------------------------------------------------------


class TestMarkAsRead:
    """Opening thread_detail should upsert ThreadReadState with is_read=True."""

    def test_non_htmx_redirects_to_thread_list(self, client, admin_user, thread):
        """Non-HTMX GET to thread_detail redirects to thread list with ?open=pk."""
        client.force_login(admin_user)
        url = reverse("emails:thread_detail", args=[thread.pk])
        response = client.get(url)
        assert response.status_code == 302
        assert f"?open={thread.pk}" in response.url

    def test_opening_thread_creates_read_state(self, client, admin_user, thread):
        """First open creates ThreadReadState with is_read=True and read_at set."""
        client.force_login(admin_user)
        url = reverse("emails:thread_detail", args=[thread.pk])
        response = client.get(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 200

        rs = ThreadReadState.objects.get(thread=thread, user=admin_user)
        assert rs.is_read is True
        assert rs.read_at is not None

    def test_reopening_thread_updates_read_at(self, client, admin_user, thread):
        """Opening an already-read thread updates read_at timestamp."""
        client.force_login(admin_user)
        # First open
        ThreadReadState.objects.create(
            thread=thread,
            user=admin_user,
            is_read=True,
            read_at=timezone.now() - timedelta(hours=2),
        )
        old_read_at = ThreadReadState.objects.get(thread=thread, user=admin_user).read_at

        url = reverse("emails:thread_detail", args=[thread.pk])
        client.get(url, HTTP_HX_REQUEST="true")

        rs = ThreadReadState.objects.get(thread=thread, user=admin_user)
        assert rs.is_read is True
        assert rs.read_at > old_read_at

    def test_new_message_after_read_makes_thread_unread(self, client, admin_user, thread, db):
        """If last_message_at > read_at, the thread is annotated as unread."""
        from apps.emails.views import annotate_unread

        # User read the thread 2 hours ago
        ThreadReadState.objects.create(
            thread=thread,
            user=admin_user,
            is_read=True,
            read_at=timezone.now() - timedelta(hours=2),
        )
        # New message arrived 30 minutes ago
        thread.last_message_at = timezone.now() - timedelta(minutes=30)
        thread.save()

        qs = annotate_unread(Thread.objects.filter(pk=thread.pk), admin_user)
        t = qs.first()
        assert t.is_unread is True


# ---------------------------------------------------------------------------
# TestMarkAsUnread -- POST to mark_thread_unread endpoint
# ---------------------------------------------------------------------------


class TestMarkAsUnread:
    """POST to mark_thread_unread sets is_read=False."""

    def test_mark_unread_sets_is_read_false(self, client, admin_user, thread):
        """POST marks the thread as unread for the user."""
        client.force_login(admin_user)
        ThreadReadState.objects.create(
            thread=thread, user=admin_user, is_read=True, read_at=timezone.now()
        )

        url = reverse("emails:mark_thread_unread", args=[thread.pk])
        response = client.post(url)
        assert response.status_code == 200

        rs = ThreadReadState.objects.get(thread=thread, user=admin_user)
        assert rs.is_read is False
        assert rs.read_at is None

    def test_mark_unread_get_returns_405(self, client, admin_user, thread):
        """GET to mark_thread_unread is not allowed."""
        client.force_login(admin_user)
        url = reverse("emails:mark_thread_unread", args=[thread.pk])
        response = client.get(url)
        assert response.status_code == 405

    def test_mark_unread_anonymous_redirects(self, client, thread):
        """Anonymous user gets redirected (302)."""
        url = reverse("emails:mark_thread_unread", args=[thread.pk])
        response = client.post(url)
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# TestUnreadAnnotation -- annotate_unread helper
# ---------------------------------------------------------------------------


class TestUnreadAnnotation:
    """Test the annotate_unread() queryset annotation."""

    def test_no_read_state_row_treated_as_read(self, admin_user, thread):
        """Thread with no ThreadReadState row is treated as read (is_unread=False)."""
        from apps.emails.views import annotate_unread

        qs = annotate_unread(Thread.objects.filter(pk=thread.pk), admin_user)
        t = qs.first()
        assert t.is_unread is False

    def test_is_read_false_annotated_as_unread(self, admin_user, thread):
        """Thread with is_read=False is annotated as is_unread=True."""
        from apps.emails.views import annotate_unread

        ThreadReadState.objects.create(
            thread=thread, user=admin_user, is_read=False, read_at=None
        )

        qs = annotate_unread(Thread.objects.filter(pk=thread.pk), admin_user)
        t = qs.first()
        assert t.is_unread is True

    def test_read_at_before_last_message_is_unread(self, admin_user, thread):
        """Thread with read_at < last_message_at is annotated as is_unread=True."""
        from apps.emails.views import annotate_unread

        thread.last_message_at = timezone.now()
        thread.save()
        ThreadReadState.objects.create(
            thread=thread,
            user=admin_user,
            is_read=True,
            read_at=timezone.now() - timedelta(hours=1),
        )

        qs = annotate_unread(Thread.objects.filter(pk=thread.pk), admin_user)
        t = qs.first()
        assert t.is_unread is True

    def test_read_at_after_last_message_is_read(self, admin_user, thread):
        """Thread with read_at >= last_message_at is annotated as is_unread=False."""
        from apps.emails.views import annotate_unread

        thread.last_message_at = timezone.now() - timedelta(hours=2)
        thread.save()
        ThreadReadState.objects.create(
            thread=thread,
            user=admin_user,
            is_read=True,
            read_at=timezone.now(),
        )

        qs = annotate_unread(Thread.objects.filter(pk=thread.pk), admin_user)
        t = qs.first()
        assert t.is_unread is False


# ---------------------------------------------------------------------------
# TestAssignmentResetsReadState -- assign_thread_view resets read state
# ---------------------------------------------------------------------------


class TestAssignmentResetsReadState:
    """Assigning a thread to a user resets their ThreadReadState to unread."""

    def test_assignment_creates_unread_state_for_assignee(
        self, client, admin_user, member_user, thread
    ):
        """Assigning thread to member creates ThreadReadState with is_read=False."""
        client.force_login(admin_user)
        url = reverse("emails:assign_thread", args=[thread.pk])
        response = client.post(url, {"assignee_id": member_user.pk})
        assert response.status_code == 200

        rs = ThreadReadState.objects.get(thread=thread, user=member_user)
        assert rs.is_read is False
        assert rs.read_at is None


# ---------------------------------------------------------------------------
# TestSidebarUnreadCounts -- thread_list context includes unread counts
# ---------------------------------------------------------------------------


class TestSidebarUnreadCounts:
    """thread_list context should include unread sidebar counts."""

    def test_sidebar_counts_include_unread_keys(self, client, admin_user, thread):
        """sidebar_counts dict includes unread_mine, unread_unassigned, unread_open, unread_closed."""
        client.force_login(admin_user)
        url = reverse("emails:thread_list")
        response = client.get(url)
        assert response.status_code == 200

        sidebar = response.context["sidebar_counts"]
        assert "unread_mine" in sidebar
        assert "unread_unassigned" in sidebar
        assert "unread_open" in sidebar
        assert "unread_closed" in sidebar
