"""Tests for Triage Lead role: category scoping, permissions, and zero-is_admin verification."""

import re

import pytest
from django.test import Client

from conftest import create_thread


@pytest.mark.django_db
class TestTriageLeadCategoryScoping:
    """ROLE-02: Triage Lead sees only threads in assigned categories."""

    def test_triage_lead_sees_assigned_category_threads(self, client, triage_lead_user):
        """Triage Lead with AssignmentRule for 'General Inquiry' sees only those threads."""
        from apps.emails.models import AssignmentRule

        AssignmentRule.objects.create(
            assignee=triage_lead_user, category="General Inquiry", is_active=True
        )
        create_thread(category="General Inquiry", subject="Visible Thread")
        create_thread(category="Sales Lead", subject="Hidden Thread")
        client.force_login(triage_lead_user)
        resp = client.get("/emails/")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Visible Thread" in content
        assert "Hidden Thread" not in content

    def test_triage_lead_no_rules_sees_empty(self, client, triage_lead_user):
        """Triage Lead with no AssignmentRules sees empty thread list."""
        create_thread(category="General Inquiry")
        client.force_login(triage_lead_user)
        resp = client.get("/emails/")
        assert resp.status_code == 200
        content = resp.content.decode()
        # Should show 0 threads
        assert "0 thread" in content

    def test_sidebar_counts_scoped_to_categories(self, client, triage_lead_user):
        """Sidebar counts reflect only triage lead's scoped categories."""
        from apps.emails.models import AssignmentRule

        AssignmentRule.objects.create(
            assignee=triage_lead_user, category="General Inquiry", is_active=True
        )
        create_thread(category="General Inquiry", status="new")
        create_thread(category="General Inquiry", status="new")
        create_thread(category="Sales Lead", status="new")  # not in scope
        client.force_login(triage_lead_user)
        resp = client.get("/emails/")
        assert resp.status_code == 200
        # The out-of-scope thread should not inflate counts


@pytest.mark.django_db
class TestTriageLeadPermissions:
    """ROLE-06: Permission enforcement for Triage Lead."""

    def test_triage_lead_can_assign_thread(self, client, triage_lead_user):
        """Triage Lead can POST to assign endpoint (not 403)."""
        from apps.accounts.models import User

        member = User.objects.create_user(
            username="m1",
            password="p",
            email="m1@vidarbhainfotech.com",
            role="member",
            is_active=True,
        )
        thread = create_thread()
        client.force_login(triage_lead_user)
        resp = client.post(
            f"/emails/threads/{thread.pk}/assign/", {"assignee_id": member.pk}
        )
        assert resp.status_code != 403

    def test_member_cannot_assign_thread(self, client, member_user):
        """Member gets 403 on assign endpoint."""
        thread = create_thread()
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread.pk}/assign/", {"assignee_id": 1}
        )
        assert resp.status_code == 403

    def test_triage_lead_can_view_settings(self, client, triage_lead_user):
        """Triage Lead gets 200 on settings page (read-only access)."""
        client.force_login(triage_lead_user)
        resp = client.get("/emails/settings/")
        assert resp.status_code == 200

    def test_triage_lead_cannot_force_poll(self, client, triage_lead_user):
        """Triage Lead gets 403 on force poll."""
        client.force_login(triage_lead_user)
        resp = client.post("/emails/inspect/force-poll/")
        assert resp.status_code == 403

    def test_member_cannot_view_settings(self, client, member_user):
        """Member gets 403 on settings page."""
        client.force_login(member_user)
        resp = client.get("/emails/settings/")
        assert resp.status_code == 403

    def test_triage_lead_can_view_inspect(self, client, triage_lead_user):
        """Triage Lead gets 200 on inspect page (view-only)."""
        client.force_login(triage_lead_user)
        resp = client.get("/emails/inspect/")
        assert resp.status_code == 200

    def test_member_cannot_view_inspect(self, client, member_user):
        """Member gets 403 on inspect page."""
        client.force_login(member_user)
        resp = client.get("/emails/inspect/")
        assert resp.status_code == 403

    def test_triage_lead_can_edit_ai_summary(self, client, triage_lead_user):
        """Triage Lead can POST to edit-summary endpoint (not 403)."""
        thread = create_thread()
        client.force_login(triage_lead_user)
        resp = client.post(
            f"/emails/threads/{thread.pk}/edit-summary/",
            {"ai_summary": "Updated summary"},
        )
        assert resp.status_code != 403

    def test_member_cannot_edit_ai_summary(self, client, member_user):
        """Member gets 403 on edit-summary endpoint."""
        thread = create_thread()
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread.pk}/edit-summary/",
            {"ai_summary": "Updated summary"},
        )
        assert resp.status_code == 403

    def test_triage_lead_can_view_reports(self, client, triage_lead_user):
        """Triage Lead gets 200 on reports page."""
        client.force_login(triage_lead_user)
        resp = client.get("/emails/reports/")
        assert resp.status_code == 200

    def test_member_cannot_view_reports(self, client, member_user):
        """Member gets 403 on reports page."""
        client.force_login(member_user)
        resp = client.get("/emails/reports/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestZeroInlineIsAdmin:
    """ROLE-06: Verify no inline is_admin patterns remain."""

    def test_no_is_admin_variable_in_emails_views(self):
        """No is_admin = ... pattern in emails/views.py."""
        with open("apps/emails/views.py") as f:
            content = f.read()
        matches = re.findall(r"is_admin\s*=\s*request\.user\.is_staff", content)
        assert len(matches) == 0, f"Found {len(matches)} inline is_admin patterns"

    def test_no_is_admin_context_variable_in_emails_views(self):
        """No 'is_admin' key in template context dicts."""
        with open("apps/emails/views.py") as f:
            content = f.read()
        matches = re.findall(r'"is_admin"\s*:', content)
        assert len(matches) == 0, f"Found {len(matches)} is_admin context variables"
