"""Tests for the thread context menu endpoint: role-aware actions, state-dependent visibility."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import CategoryVisibility, Thread
from conftest import create_thread


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.login(username="admin", password="testpass123")
    return c


@pytest.fixture
def member_client(member_user):
    c = Client()
    c.login(username="member", password="testpass123")
    return c


class TestContextMenuEndpoint:
    """GET /emails/threads/<pk>/context-menu/ returns role-aware HTML partial."""

    def test_returns_200_for_authenticated_user(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert resp.status_code == 200

    def test_unauthenticated_redirects(self, client, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url

    def test_post_not_allowed(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.post(url)
        assert resp.status_code == 405

    def test_admin_sees_assign_option(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert b"Assign to" in resp.content

    def test_admin_sees_whitelist_option(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert b"Whitelist Sender" in resp.content

    def test_member_sees_claim_instead_of_assign(self, member_client, member_user, db):
        thread = create_thread()
        CategoryVisibility.objects.create(user=member_user, category=thread.category)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Claim" in resp.content
        assert b"Assign to" not in resp.content

    def test_member_does_not_see_whitelist(self, member_client, member_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Whitelist Sender" not in resp.content

    def test_acknowledged_thread_hides_acknowledge_action(self, admin_client, admin_user, db):
        thread = create_thread(status=Thread.Status.ACKNOWLEDGED)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert b"Acknowledge" not in resp.content

    def test_closed_thread_hides_close_action(self, admin_client, admin_user, db):
        thread = create_thread(status=Thread.Status.CLOSED)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert b"Close" not in resp.content or resp.content.count(b"Close") == 0

    def test_new_thread_shows_acknowledge_and_close(self, admin_client, admin_user, db):
        thread = create_thread(status=Thread.Status.NEW)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert b"Acknowledge" in resp.content
        assert b"Close" in resp.content

    def test_member_cannot_claim_if_already_assigned_to_them(self, member_client, member_user, db):
        thread = create_thread(assigned_to=member_user)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Claim" not in resp.content

    def test_menu_contains_keyboard_shortcuts(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        content = resp.content.decode()
        # Check shortcut hints are present
        assert "kbd" in content or "shortcut" in content.lower()

    def test_menu_has_menuitem_roles(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        assert b'role="menuitem"' in resp.content

    def test_404_for_nonexistent_thread(self, admin_client, admin_user, db):
        url = reverse("emails:thread_context_menu", args=[99999])
        resp = admin_client.get(url)
        assert resp.status_code == 404

    def test_admin_sees_claim_for_unassigned_thread(self, admin_client, admin_user, db):
        """Admin should see Claim in context menu for unassigned threads."""
        thread = create_thread()  # unassigned by default
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = admin_client.get(url)
        # Admin sees both Assign and Claim for unassigned threads
        assert b"Claim" in resp.content

    def test_no_claim_for_assigned_thread(self, member_client, member_user, admin_user, db):
        """Member should NOT see Claim for a thread assigned to someone else."""
        thread = create_thread(assigned_to=admin_user)
        CategoryVisibility.objects.create(user=member_user, category=thread.category)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Claim" not in resp.content

    def test_no_claim_for_closed_thread(self, member_client, member_user, db):
        """No Claim option on a closed unassigned thread."""
        thread = create_thread(status=Thread.Status.CLOSED)
        CategoryVisibility.objects.create(user=member_user, category=thread.category)
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Claim" not in resp.content

    def test_member_can_claim_without_category_visibility(self, member_client, member_user, db):
        """Member with no CategoryVisibility rows can claim any thread (default-open)."""
        thread = create_thread()
        # No CategoryVisibility created — should default to all categories visible
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Claim" in resp.content

    def test_member_no_claim_with_restricted_visibility(self, member_client, member_user, db):
        """Member with explicit CategoryVisibility rows cannot claim outside their categories."""
        thread = create_thread()
        # Give member visibility to a DIFFERENT category only
        CategoryVisibility.objects.create(user=member_user, category="Other Category")
        url = reverse("emails:thread_context_menu", args=[thread.pk])
        resp = member_client.get(url)
        assert b"Claim" not in resp.content
