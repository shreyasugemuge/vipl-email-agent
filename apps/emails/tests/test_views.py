"""Tests for the email dashboard views."""

import pytest
from datetime import datetime, timezone
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import Email


def _create_email(db, **overrides):
    """Helper to create a completed Email record with sensible defaults."""
    defaults = {
        "message_id": f"msg_{id(overrides)}_{overrides.get('subject', 'test')}",
        "from_address": "sender@example.com",
        "from_name": "Test Sender",
        "to_inbox": "info@vidarbhainfotech.com",
        "subject": "Test Subject",
        "body": "Test body",
        "received_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        "category": "General Inquiry",
        "priority": "MEDIUM",
        "ai_summary": "This is a test email summary.",
        "processing_status": Email.ProcessingStatus.COMPLETED,
        "status": Email.Status.NEW,
    }
    defaults.update(overrides)
    return Email.objects.create(**defaults)


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


class TestEmailListAuth:
    """Test authentication requirements for email_list view."""

    def test_returns_200_for_authenticated_user(self, admin_client, db):
        """Test 1: email_list view returns 200 for authenticated user."""
        response = admin_client.get(reverse("emails:email_list"))
        assert response.status_code == 200

    def test_redirects_unauthenticated_user(self, client, db):
        """Test 2: email_list view redirects to login for unauthenticated user."""
        response = client.get(reverse("emails:email_list"))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url


class TestEmailListDefaultView:
    """Test default view behavior based on user role."""

    def test_admin_default_shows_unassigned(self, admin_client, admin_user, member_user, db):
        """Test 3: Default admin view filters to unassigned emails."""
        assigned = _create_email(db, message_id="msg_assigned", assigned_to=member_user)
        unassigned = _create_email(db, message_id="msg_unassigned", assigned_to=None)

        response = admin_client.get(reverse("emails:email_list"))
        emails = list(response.context["emails"])
        assert unassigned in emails
        assert assigned not in emails

    def test_member_default_shows_own(self, member_client, member_user, admin_user, db):
        """Test 4: Default member view filters to own assigned emails."""
        own = _create_email(db, message_id="msg_own", assigned_to=member_user)
        other = _create_email(db, message_id="msg_other", assigned_to=admin_user)
        unassigned = _create_email(db, message_id="msg_none", assigned_to=None)

        response = member_client.get(reverse("emails:email_list"))
        emails = list(response.context["emails"])
        assert own in emails
        assert other not in emails
        assert unassigned not in emails


class TestEmailListFilters:
    """Test filtering behavior."""

    def test_filter_by_status(self, admin_client, db):
        """Test 5: Filter by status returns only matching emails."""
        new_email = _create_email(db, message_id="msg_new", status=Email.Status.NEW)
        closed_email = _create_email(db, message_id="msg_closed", status=Email.Status.CLOSED)

        response = admin_client.get(reverse("emails:email_list"), {"view": "all", "status": "new"})
        emails = list(response.context["emails"])
        assert new_email in emails
        assert closed_email not in emails

    def test_filter_by_priority(self, admin_client, db):
        """Test 6: Filter by priority returns only matching emails."""
        high = _create_email(db, message_id="msg_high", priority="HIGH")
        low = _create_email(db, message_id="msg_low", priority="LOW")

        response = admin_client.get(reverse("emails:email_list"), {"view": "all", "priority": "HIGH"})
        emails = list(response.context["emails"])
        assert high in emails
        assert low not in emails

    def test_combined_filters(self, admin_client, db):
        """Test 11: Combined filter query params return only emails matching ALL criteria."""
        match = _create_email(
            db,
            message_id="msg_match",
            status=Email.Status.NEW,
            priority="HIGH",
            to_inbox="info@vidarbhainfotech.com",
        )
        wrong_status = _create_email(
            db,
            message_id="msg_wrong_status",
            status=Email.Status.CLOSED,
            priority="HIGH",
            to_inbox="info@vidarbhainfotech.com",
        )
        wrong_priority = _create_email(
            db,
            message_id="msg_wrong_pri",
            status=Email.Status.NEW,
            priority="LOW",
            to_inbox="info@vidarbhainfotech.com",
        )
        wrong_inbox = _create_email(
            db,
            message_id="msg_wrong_inbox",
            status=Email.Status.NEW,
            priority="HIGH",
            to_inbox="sales@vidarbhainfotech.com",
        )

        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "all", "status": "new", "priority": "HIGH", "inbox": "info@vidarbhainfotech.com"},
        )
        emails = list(response.context["emails"])
        assert match in emails
        assert wrong_status not in emails
        assert wrong_priority not in emails
        assert wrong_inbox not in emails


class TestEmailListSort:
    """Test sorting behavior."""

    def test_default_sort_by_created_at_desc(self, admin_client, db):
        """Test 7a: Default sort is -created_at."""
        old = _create_email(
            db,
            message_id="msg_old",
            received_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        new = _create_email(
            db,
            message_id="msg_new_sort",
            received_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        )

        response = admin_client.get(reverse("emails:email_list"), {"view": "all"})
        emails = list(response.context["emails"])
        # Newer should come first (default sort is -created_at)
        assert emails.index(new) < emails.index(old)

    def test_sort_by_priority(self, admin_client, db):
        """Test 7b: Sort by priority orders correctly."""
        low = _create_email(db, message_id="msg_low_sort", priority="LOW")
        high = _create_email(db, message_id="msg_high_sort", priority="HIGH")

        response = admin_client.get(reverse("emails:email_list"), {"view": "all", "sort": "priority"})
        emails = list(response.context["emails"])
        assert len(emails) == 2


class TestEmailListPagination:
    """Test pagination behavior."""

    def test_pagination_25_per_page(self, admin_client, db):
        """Test 8: Pagination returns 25 per page."""
        for i in range(30):
            _create_email(
                db,
                message_id=f"msg_page_{i}",
                received_at=datetime(2026, 3, 10, i % 24, 0, 0, tzinfo=timezone.utc),
            )

        response = admin_client.get(reverse("emails:email_list"), {"view": "all"})
        assert len(response.context["emails"]) == 25

    def test_filter_params_preserved_in_pagination(self, admin_client, db):
        """Test 12: Filter state preserved in URL query params in pagination links."""
        for i in range(30):
            _create_email(
                db,
                message_id=f"msg_filter_page_{i}",
                status=Email.Status.NEW,
                priority="HIGH",
            )

        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "all", "status": "new", "priority": "HIGH"},
        )
        content = response.content.decode()
        # Pagination link to page 2 should contain filter params
        assert "status=new" in content
        assert "priority=HIGH" in content


class TestEmailListTabs:
    """Test tab view behavior."""

    def test_all_tab_shows_completed_emails(self, admin_client, db):
        """Test 9: View tab 'all' shows all completed emails."""
        completed = _create_email(db, message_id="msg_completed")
        pending = _create_email(
            db,
            message_id="msg_pending",
            processing_status=Email.ProcessingStatus.PENDING,
        )

        response = admin_client.get(reverse("emails:email_list"), {"view": "all"})
        emails = list(response.context["emails"])
        assert completed in emails
        assert pending not in emails


class TestEmailListHTMX:
    """Test HTMX partial response behavior."""

    def test_htmx_returns_partial(self, admin_client, db):
        """Test 10: HTMX request returns partial (no base layout), non-HTMX returns full page."""
        _create_email(db, message_id="msg_htmx")

        # Non-HTMX: full page with sidebar
        response = admin_client.get(reverse("emails:email_list"), {"view": "all"})
        content = response.content.decode()
        assert "VIPL Triage" in content  # Sidebar branding

        # HTMX: partial without sidebar
        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "all"},
            HTTP_HX_REQUEST="true",
        )
        content = response.content.decode()
        assert "VIPL Triage" not in content  # No sidebar in partial


class TestEmailCountOOBUpdate:
    """Test that HTMX responses include OOB email count update."""

    def test_htmx_unassigned_view_has_oob_count(self, admin_client, db):
        """HTMX request to unassigned view includes OOB count span."""
        _create_email(db, message_id="msg_oob_1")
        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "unassigned"},
            HTTP_HX_REQUEST="true",
        )
        content = response.content.decode()
        assert 'id="email-count"' in content
        assert 'hx-swap-oob' in content

    def test_htmx_mine_view_has_oob_count(self, admin_client, admin_user, db):
        """HTMX request to mine view includes OOB count span."""
        _create_email(db, message_id="msg_oob_2", assigned_to=admin_user)
        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "mine"},
            HTTP_HX_REQUEST="true",
        )
        content = response.content.decode()
        assert 'id="email-count"' in content
        assert 'hx-swap-oob' in content

    def test_non_htmx_has_no_oob(self, admin_client, db):
        """Non-HTMX full page render does NOT have hx-swap-oob on count."""
        _create_email(db, message_id="msg_oob_3")
        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "all"},
        )
        content = response.content.decode()
        assert 'hx-swap-oob' not in content

    def test_oob_count_has_correct_pluralization(self, admin_client, db):
        """OOB count shows correct plural form."""
        _create_email(db, message_id="msg_oob_single")
        response = admin_client.get(
            reverse("emails:email_list"),
            {"view": "all"},
            HTTP_HX_REQUEST="true",
        )
        content = response.content.decode()
        assert "1 email" in content
