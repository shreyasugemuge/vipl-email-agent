"""Tests for inline edit endpoints: edit_category, edit_priority, edit_status."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import ActivityLog, Thread
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


class TestEditCategory:
    """Inline category edit endpoint."""

    def test_standard_category_update(self, admin_client, admin_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = admin_client.post(url, {"category": "Sales Lead"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.category == "Sales Lead"
        assert thread.category_overridden is True

    def test_custom_category(self, admin_client, admin_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = admin_client.post(url, {"category": "__custom__", "custom_category": "My Custom"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.category == "My Custom"
        assert thread.category_overridden is True

    def test_custom_category_empty_returns_400(self, admin_client, admin_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = admin_client.post(url, {"category": "__custom__", "custom_category": ""})
        assert resp.status_code == 400

    def test_custom_category_too_long_returns_400(self, admin_client, admin_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = admin_client.post(url, {"category": "__custom__", "custom_category": "x" * 101})
        assert resp.status_code == 400

    def test_activity_log_created(self, admin_client, admin_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        admin_client.post(url, {"category": "Complaint"})
        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.CATEGORY_CHANGED).first()
        assert log is not None
        assert log.old_value == "General Inquiry"
        assert log.new_value == "Complaint"
        assert log.user == admin_user

    def test_returns_detail_html(self, admin_client, admin_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = admin_client.post(url, {"category": "Sales Lead"})
        assert resp.status_code == 200
        assert b"thread-scroll-container" in resp.content  # detail partial rendered

    def test_non_post_returns_405(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = admin_client.get(url)
        assert resp.status_code == 405

    def test_unauthenticated_redirects(self, client, db):
        thread = create_thread()
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = client.post(url, {"category": "Sales Lead"})
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url

    def test_member_can_edit_category(self, member_client, member_user, db):
        thread = create_thread(category="General Inquiry")
        url = reverse("emails:edit_category", args=[thread.pk])
        resp = member_client.post(url, {"category": "Complaint"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.category == "Complaint"


class TestEditPriority:
    """Inline priority edit endpoint."""

    def test_valid_priority_update(self, admin_client, admin_user, db):
        thread = create_thread(priority="MEDIUM")
        url = reverse("emails:edit_priority", args=[thread.pk])
        resp = admin_client.post(url, {"priority": "HIGH"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.priority == "HIGH"
        assert thread.priority_overridden is True

    def test_invalid_priority_returns_400(self, admin_client, admin_user, db):
        thread = create_thread(priority="MEDIUM")
        url = reverse("emails:edit_priority", args=[thread.pk])
        resp = admin_client.post(url, {"priority": "INVALID"})
        assert resp.status_code == 400

    def test_activity_log_created(self, admin_client, admin_user, db):
        thread = create_thread(priority="LOW")
        url = reverse("emails:edit_priority", args=[thread.pk])
        admin_client.post(url, {"priority": "CRITICAL"})
        log = ActivityLog.objects.filter(thread=thread, action=ActivityLog.Action.PRIORITY_CHANGED).first()
        assert log is not None
        assert log.old_value == "LOW"
        assert log.new_value == "CRITICAL"

    def test_non_post_returns_405(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:edit_priority", args=[thread.pk])
        resp = admin_client.get(url)
        assert resp.status_code == 405

    def test_unauthenticated_redirects(self, client, db):
        thread = create_thread()
        url = reverse("emails:edit_priority", args=[thread.pk])
        resp = client.post(url, {"priority": "HIGH"})
        assert resp.status_code == 302

    def test_member_can_edit_priority(self, member_client, member_user, db):
        thread = create_thread(priority="LOW")
        url = reverse("emails:edit_priority", args=[thread.pk])
        resp = member_client.post(url, {"priority": "HIGH"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.priority == "HIGH"


class TestEditStatus:
    """Inline status edit endpoint."""

    def test_admin_can_change_status(self, admin_client, admin_user, db):
        thread = create_thread(status=Thread.Status.NEW)
        url = reverse("emails:edit_status", args=[thread.pk])
        resp = admin_client.post(url, {"new_status": "acknowledged"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.status == "acknowledged"

    def test_assigned_user_can_change_status(self, member_client, member_user, db):
        thread = create_thread(status=Thread.Status.NEW, assigned_to=member_user)
        url = reverse("emails:edit_status", args=[thread.pk])
        resp = member_client.post(url, {"new_status": "acknowledged"})
        assert resp.status_code == 200
        thread.refresh_from_db()
        assert thread.status == "acknowledged"

    def test_non_assigned_member_forbidden(self, member_client, member_user, admin_user, db):
        thread = create_thread(status=Thread.Status.NEW, assigned_to=admin_user)
        url = reverse("emails:edit_status", args=[thread.pk])
        resp = member_client.post(url, {"new_status": "acknowledged"})
        assert resp.status_code == 403

    def test_activity_log_created(self, admin_client, admin_user, db):
        thread = create_thread(status=Thread.Status.NEW)
        url = reverse("emails:edit_status", args=[thread.pk])
        admin_client.post(url, {"new_status": "acknowledged"})
        log = ActivityLog.objects.filter(thread=thread).exclude(
            action=ActivityLog.Action.THREAD_CREATED
        ).first()
        assert log is not None

    def test_non_post_returns_405(self, admin_client, admin_user, db):
        thread = create_thread()
        url = reverse("emails:edit_status", args=[thread.pk])
        resp = admin_client.get(url)
        assert resp.status_code == 405

    def test_unauthenticated_redirects(self, client, db):
        thread = create_thread()
        url = reverse("emails:edit_status", args=[thread.pk])
        resp = client.post(url, {"new_status": "acknowledged"})
        assert resp.status_code == 302

    def test_returns_detail_and_oob_card(self, admin_client, admin_user, db):
        thread = create_thread(status=Thread.Status.NEW)
        url = reverse("emails:edit_status", args=[thread.pk])
        resp = admin_client.post(url, {"new_status": "acknowledged"})
        assert resp.status_code == 200
        assert b"thread-scroll-container" in resp.content
