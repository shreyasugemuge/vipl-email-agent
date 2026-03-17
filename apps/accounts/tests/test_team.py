"""Tests for team management views."""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.emails.models import ActivityLog, AssignmentRule, CategoryVisibility, Thread, ThreadViewer


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


@pytest.fixture
def triage_lead_client(triage_lead_user):
    c = Client()
    c.login(username="triage_lead", password="testpass123")
    return c


@pytest.mark.django_db
class TestTeamListView:
    def test_admin_can_access(self, admin_client):
        response = admin_client.get("/accounts/team/")
        assert response.status_code == 200

    def test_member_forbidden(self, member_client):
        response = member_client.get("/accounts/team/")
        assert response.status_code == 403

    def test_unauthenticated_redirects(self, client):
        response = client.get("/accounts/team/")
        assert response.status_code == 302

    def test_lists_all_users(self, admin_client, admin_user, member_user):
        response = admin_client.get("/accounts/team/")
        user_pks = [u.pk for u in response.context["team_users"]]
        assert admin_user.pk in user_pks
        assert member_user.pk in user_pks

    def test_stats_correct(self, admin_client, admin_user, member_user):
        response = admin_client.get("/accounts/team/")
        stats = response.context["stats"]
        assert stats["total"] == 2
        assert stats["active"] == 2
        assert stats["admins"] == 1

    def test_pending_users_shown(self, admin_client, admin_user):
        User.objects.create_user(username="pending", password="x", is_active=False)
        response = admin_client.get("/accounts/team/")
        stats = response.context["stats"]
        assert stats["pending"] == 1


@pytest.mark.django_db
class TestToggleActive:
    def test_approve_pending_user(self, admin_client, db):
        pending = User.objects.create_user(
            username="newguy", password="x", is_active=False,
        )
        response = admin_client.post(f"/accounts/team/{pending.pk}/toggle-active/")
        assert response.status_code == 200
        pending.refresh_from_db()
        assert pending.is_active is True

    def test_deactivate_member(self, admin_client, member_user):
        response = admin_client.post(f"/accounts/team/{member_user.pk}/toggle-active/")
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.is_active is False

    def test_deactivate_unassigns_open_threads(self, admin_client, admin_user, member_user):
        """Deactivating a user unassigns their open threads and logs activity."""
        t1 = Thread.objects.create(
            gmail_thread_id="deact-1", subject="Thread 1",
            assigned_to=member_user, status="acknowledged",
        )
        t2 = Thread.objects.create(
            gmail_thread_id="deact-2", subject="Thread 2",
            assigned_to=member_user, status="new",
        )
        # Closed thread should NOT be unassigned
        t3 = Thread.objects.create(
            gmail_thread_id="deact-3", subject="Closed",
            assigned_to=member_user, status="closed",
        )
        admin_client.post(f"/accounts/team/{member_user.pk}/toggle-active/")

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()
        assert t1.assigned_to is None
        assert t1.status == "new"
        assert t2.assigned_to is None
        assert t2.status == "new"
        # Closed thread untouched
        assert t3.assigned_to == member_user
        assert t3.status == "closed"
        # Activity log entries created
        assert ActivityLog.objects.filter(thread=t1, action="unassigned").exists()
        assert ActivityLog.objects.filter(thread=t2, action="unassigned").exists()

    def test_deactivate_removes_assignment_rules(self, admin_client, member_user):
        """Deactivating a user removes their AssignmentRule entries."""
        AssignmentRule.objects.create(category="billing", assignee=member_user)
        admin_client.post(f"/accounts/team/{member_user.pk}/toggle-active/")
        assert AssignmentRule.objects.filter(assignee=member_user).count() == 0

    def test_deactivate_clears_thread_viewers(self, admin_client, member_user):
        """Deactivating a user clears their ThreadViewer records."""
        t = Thread.objects.create(gmail_thread_id="viewer-1", subject="V")
        ThreadViewer.objects.create(thread=t, user=member_user)
        admin_client.post(f"/accounts/team/{member_user.pk}/toggle-active/")
        assert ThreadViewer.objects.filter(user=member_user).count() == 0

    def test_cannot_deactivate_self(self, admin_client, admin_user):
        response = admin_client.post(f"/accounts/team/{admin_user.pk}/toggle-active/")
        assert response.status_code == 403
        admin_user.refresh_from_db()
        assert admin_user.is_active is True

    def test_member_forbidden(self, member_client, admin_user):
        response = member_client.post(f"/accounts/team/{admin_user.pk}/toggle-active/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestChangeRole:
    def test_promote_member_to_admin(self, admin_client, member_user):
        response = admin_client.post(
            f"/accounts/team/{member_user.pk}/change-role/",
            {"role": "admin"},
        )
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.role == User.Role.ADMIN
        assert member_user.is_staff is True

    def test_demote_other_admin(self, admin_client, db):
        other = User.objects.create_user(
            username="admin2", password="x", role=User.Role.ADMIN, is_staff=True,
        )
        response = admin_client.post(
            f"/accounts/team/{other.pk}/change-role/", {"role": "member"},
        )
        assert response.status_code == 200
        other.refresh_from_db()
        assert other.role == User.Role.MEMBER
        assert other.is_staff is False

    def test_cannot_remove_own_admin(self, admin_client, admin_user):
        response = admin_client.post(
            f"/accounts/team/{admin_user.pk}/change-role/", {"role": "member"},
        )
        assert response.status_code == 403

    def test_invalid_role_rejected(self, admin_client, member_user):
        response = admin_client.post(
            f"/accounts/team/{member_user.pk}/change-role/", {"role": "superadmin"},
        )
        assert response.status_code == 403

    def test_member_forbidden(self, member_client, admin_user):
        response = member_client.post(
            f"/accounts/team/{admin_user.pk}/change-role/", {"role": "member"},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestToggleVisibility:
    def test_toggle_on(self, admin_client, member_user):
        assert member_user.can_see_all_emails is False
        response = admin_client.post(f"/accounts/team/{member_user.pk}/toggle-visibility/")
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.can_see_all_emails is True

    def test_toggle_off(self, admin_client, member_user):
        member_user.can_see_all_emails = True
        member_user.save()
        response = admin_client.post(f"/accounts/team/{member_user.pk}/toggle-visibility/")
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.can_see_all_emails is False

    def test_member_forbidden(self, member_client, admin_user):
        response = member_client.post(f"/accounts/team/{admin_user.pk}/toggle-visibility/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestSaveCategories:
    def test_set_categories(self, admin_client, member_user):
        response = admin_client.post(
            f"/accounts/team/{member_user.pk}/categories/",
            {"categories": ["General Inquiry", "Complaint"]},
        )
        assert response.status_code == 200
        cats = set(CategoryVisibility.objects.filter(user=member_user).values_list("category", flat=True))
        assert "General Inquiry" in cats
        assert "Complaint" in cats

    def test_replace_categories(self, admin_client, member_user):
        CategoryVisibility.objects.create(user=member_user, category="General Inquiry")
        response = admin_client.post(
            f"/accounts/team/{member_user.pk}/categories/",
            {"categories": ["Complaint"]},
        )
        assert response.status_code == 200
        cats = list(CategoryVisibility.objects.filter(user=member_user).values_list("category", flat=True))
        assert cats == ["Complaint"]

    def test_clear_categories(self, admin_client, member_user):
        CategoryVisibility.objects.create(user=member_user, category="General Inquiry")
        response = admin_client.post(f"/accounts/team/{member_user.pk}/categories/")
        assert response.status_code == 200
        assert CategoryVisibility.objects.filter(user=member_user).count() == 0

    def test_invalid_category_ignored(self, admin_client, member_user):
        response = admin_client.post(
            f"/accounts/team/{member_user.pk}/categories/",
            {"categories": ["FakeCategory", "General Inquiry"]},
        )
        assert response.status_code == 200
        cats = list(CategoryVisibility.objects.filter(user=member_user).values_list("category", flat=True))
        assert "FakeCategory" not in cats
        assert "General Inquiry" in cats

    def test_member_forbidden(self, member_client, admin_user):
        response = member_client.post(
            f"/accounts/team/{admin_user.pk}/categories/",
            {"categories": ["General Inquiry"]},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTriageLeadRole:
    """Tests for Triage Lead promotion/demotion and team page access."""

    def test_admin_can_promote_to_triage_lead(self, admin_client, member_user):
        response = admin_client.post(
            f"/accounts/team/{member_user.pk}/change-role/",
            {"role": "triage_lead"},
        )
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.role == "triage_lead"
        assert member_user.is_staff is False

    def test_admin_can_demote_triage_lead_to_member(self, admin_client, triage_lead_user):
        response = admin_client.post(
            f"/accounts/team/{triage_lead_user.pk}/change-role/",
            {"role": "member"},
        )
        assert response.status_code == 200
        triage_lead_user.refresh_from_db()
        assert triage_lead_user.role == "member"

    def test_triage_lead_cannot_change_roles(self, triage_lead_client, member_user):
        response = triage_lead_client.post(
            f"/accounts/team/{member_user.pk}/change-role/",
            {"role": "admin"},
        )
        assert response.status_code == 403

    def test_triage_lead_can_view_team_page(self, triage_lead_client):
        response = triage_lead_client.get("/accounts/team/")
        assert response.status_code == 200

    def test_triage_lead_can_toggle_active(self, triage_lead_client, member_user):
        response = triage_lead_client.post(
            f"/accounts/team/{member_user.pk}/toggle-active/"
        )
        assert response.status_code == 200
        member_user.refresh_from_db()
        assert member_user.is_active is False

    def test_member_cannot_view_team_page(self, member_client):
        response = member_client.get("/accounts/team/")
        assert response.status_code == 403
