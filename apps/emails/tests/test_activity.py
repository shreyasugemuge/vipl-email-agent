"""Tests for the activity log view."""

import pytest
from datetime import datetime, timezone
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import Email, ActivityLog
from conftest import create_email


@pytest.fixture
def admin_client(admin_user):
    """Authenticated client logged in as admin."""
    c = Client()
    c.login(username="admin", password="testpass123")
    return c


@pytest.fixture
def member_client(member_user):
    """Authenticated client logged in as member."""
    c = Client()
    c.login(username="member", password="testpass123")
    return c


@pytest.mark.django_db
class TestActivityLogView:
    """Tests for /emails/activity/ view."""

    def test_returns_200_for_authenticated_user(self, admin_client):
        """Test 1: activity_log view returns 200 for authenticated user."""
        url = reverse("emails:activity_log")
        resp = admin_client.get(url)
        assert resp.status_code == 200

    def test_shows_activity_entries(self, admin_client, admin_user):
        """Test 2: activity_log shows entries with user, action, email subject, timestamp."""
        email = create_email(message_id="msg_act_1", subject="Important RFQ")
        ActivityLog.objects.create(
            email=email,
            user=admin_user,
            action=ActivityLog.Action.ASSIGNED,
            detail="Assigned for review",
            new_value="admin",
        )

        url = reverse("emails:activity_log")
        resp = admin_client.get(url)
        content = resp.content.decode()

        assert "admin" in content  # user name
        assert "Assigned" in content  # action label
        assert "Important RFQ" in content  # email subject

    def test_paginates_at_50_entries(self, admin_client, admin_user):
        """Test 3: activity_log paginates at 50 entries per page."""
        email = create_email(message_id="msg_act_pag")
        for i in range(55):
            ActivityLog.objects.create(
                email=email,
                user=admin_user,
                action=ActivityLog.Action.ACKNOWLEDGED,
                detail=f"Entry {i}",
            )

        url = reverse("emails:activity_log")
        resp = admin_client.get(url)
        content = resp.content.decode()

        # Page 1 should have 50, not all 55
        assert resp.context["page_obj"].paginator.count == 55
        assert len(resp.context["page_obj"]) == 50

    def test_htmx_returns_partial(self, admin_client):
        """Test 4: HTMX request returns _activity_feed.html partial."""
        url = reverse("emails:activity_log")
        resp = admin_client.get(url, HTTP_HX_REQUEST="true")
        assert resp.status_code == 200
        # Partial should NOT contain <html> or <!DOCTYPE>
        content = resp.content.decode()
        assert "<!DOCTYPE" not in content

    def test_non_htmx_returns_full_page(self, admin_client):
        """Test 5: Non-HTMX request returns full activity_log.html page."""
        url = reverse("emails:activity_log")
        resp = admin_client.get(url)
        content = resp.content.decode()
        assert "Activity" in content

    def test_entries_ordered_newest_first(self, admin_client, admin_user):
        """Test 6: entries ordered by -created_at (newest first)."""
        email = create_email(message_id="msg_act_ord")
        log1 = ActivityLog.objects.create(
            email=email,
            user=admin_user,
            action=ActivityLog.Action.ASSIGNED,
            detail="First",
        )
        log2 = ActivityLog.objects.create(
            email=email,
            user=admin_user,
            action=ActivityLog.Action.STATUS_CHANGED,
            detail="Second",
        )

        url = reverse("emails:activity_log")
        resp = admin_client.get(url)
        logs = list(resp.context["page_obj"])
        assert logs[0].pk == log2.pk  # newest first
        assert logs[1].pk == log1.pk

    def test_requires_login(self, client):
        """Unauthenticated users redirected to login."""
        url = reverse("emails:activity_log")
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url
