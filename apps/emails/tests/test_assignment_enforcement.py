"""Tests for assignment permission enforcement (Phase 2, Plan 01).

Covers ROLE-03 (only admin/gatekeeper can assign), ROLE-04 (member self-claim
with CategoryVisibility, gatekeeper bypass), and ROLE-05 (member reassign with
mandatory reason and REASSIGNED_BY_MEMBER ActivityLog action).
"""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.emails.models import ActivityLog, CategoryVisibility, Thread

from conftest import create_thread


@pytest.fixture
def target_user(db):
    """A second member user to be reassignment target."""
    return User.objects.create_user(
        username="target",
        password="testpass123",
        email="target@vidarbhainfotech.com",
        first_name="Target",
        last_name="User",
        role=User.Role.MEMBER,
        is_active=True,
    )


@pytest.fixture
def thread_general(db):
    """An unassigned thread with category 'General Inquiry'."""
    return create_thread(category="General Inquiry")


# ---------------------------------------------------------------------------
# ROLE-03: Only admin/gatekeeper can assign
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssignPermission:
    def test_admin_can_assign_thread(self, client, admin_user, member_user, thread_general):
        """Admin POSTs to assign endpoint -> 200 (not 403)."""
        client.force_login(admin_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/assign/",
            {"assignee_id": member_user.pk},
        )
        assert resp.status_code == 200
        thread_general.refresh_from_db()
        assert thread_general.assigned_to == member_user

    def test_gatekeeper_can_assign_thread(self, client, triage_lead_user, member_user, thread_general):
        """Triage lead POSTs to assign endpoint -> 200 (not 403)."""
        client.force_login(triage_lead_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/assign/",
            {"assignee_id": member_user.pk},
        )
        assert resp.status_code == 200
        thread_general.refresh_from_db()
        assert thread_general.assigned_to == member_user

    def test_member_cannot_assign_thread(self, client, member_user, thread_general, target_user):
        """Member POSTs to assign endpoint -> 403 with exact message."""
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/assign/",
            {"assignee_id": target_user.pk},
        )
        assert resp.status_code == 403
        assert b"Only gatekeepers and admins can assign threads to other users." in resp.content


# ---------------------------------------------------------------------------
# ROLE-04: Member can self-claim; gatekeeper bypasses CategoryVisibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClaimPermission:
    def test_member_can_claim_unassigned_in_category(self, client, member_user, thread_general):
        """Member with CategoryVisibility POSTs to claim -> success."""
        CategoryVisibility.objects.create(user=member_user, category="General Inquiry")
        client.force_login(member_user)
        resp = client.post(f"/emails/threads/{thread_general.pk}/claim/")
        assert resp.status_code == 200
        thread_general.refresh_from_db()
        assert thread_general.assigned_to == member_user

    def test_gatekeeper_bypasses_category_visibility_on_claim(
        self, client, triage_lead_user, thread_general,
    ):
        """Triage lead claims thread outside their CategoryVisibility -> success."""
        # No CategoryVisibility created for triage_lead_user
        client.force_login(triage_lead_user)
        resp = client.post(f"/emails/threads/{thread_general.pk}/claim/")
        assert resp.status_code == 200
        thread_general.refresh_from_db()
        assert thread_general.assigned_to == triage_lead_user


# ---------------------------------------------------------------------------
# ROLE-05: Member reassign with mandatory reason
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReassignPermission:
    def test_member_reassign_own_thread_with_reason(
        self, client, member_user, target_user, thread_general,
    ):
        """Member reassigns own thread with reason -> 200, assigned_to changed."""
        thread_general.assigned_to = member_user
        thread_general.save()
        CategoryVisibility.objects.create(user=target_user, category="General Inquiry")
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/reassign/",
            {"assignee_id": target_user.pk, "reason": "I'm on leave, please handle this"},
        )
        assert resp.status_code == 200
        thread_general.refresh_from_db()
        assert thread_general.assigned_to == target_user

    def test_member_reassign_without_reason_fails(
        self, client, member_user, target_user, thread_general,
    ):
        """Member POSTs reassign with empty reason -> 403."""
        thread_general.assigned_to = member_user
        thread_general.save()
        CategoryVisibility.objects.create(user=target_user, category="General Inquiry")
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/reassign/",
            {"assignee_id": target_user.pk, "reason": ""},
        )
        assert resp.status_code == 403

    def test_member_reassign_whitespace_reason_fails(
        self, client, member_user, target_user, thread_general,
    ):
        """Member POSTs reassign with whitespace-only reason -> 403."""
        thread_general.assigned_to = member_user
        thread_general.save()
        CategoryVisibility.objects.create(user=target_user, category="General Inquiry")
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/reassign/",
            {"assignee_id": target_user.pk, "reason": "   "},
        )
        assert resp.status_code == 403

    def test_member_reassign_others_thread_fails(
        self, client, member_user, target_user, thread_general,
    ):
        """Member POSTs reassign on thread assigned to someone else -> 403."""
        thread_general.assigned_to = target_user
        thread_general.save()
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/reassign/",
            {"assignee_id": member_user.pk, "reason": "Want to take over"},
        )
        assert resp.status_code == 403

    def test_reassign_creates_reassigned_by_member_log(
        self, client, member_user, target_user, thread_general,
    ):
        """After reassign, ActivityLog has action=REASSIGNED_BY_MEMBER with reason in detail."""
        thread_general.assigned_to = member_user
        thread_general.save()
        CategoryVisibility.objects.create(user=target_user, category="General Inquiry")
        client.force_login(member_user)
        client.post(
            f"/emails/threads/{thread_general.pk}/reassign/",
            {"assignee_id": target_user.pk, "reason": "I'm on leave"},
        )
        log = ActivityLog.objects.filter(
            thread=thread_general, action="reassigned_by_member",
        ).first()
        assert log is not None
        assert "on leave" in log.detail

    def test_member_reassign_targets_filtered_by_category(
        self, client, member_user, target_user, thread_general,
    ):
        """Reassign to user without CategoryVisibility -> 403 with message."""
        thread_general.assigned_to = member_user
        thread_general.save()
        # No CategoryVisibility for target_user
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/reassign/",
            {"assignee_id": target_user.pk, "reason": "Need help"},
        )
        assert resp.status_code == 403
        assert b"does not handle" in resp.content


# ---------------------------------------------------------------------------
# Read-only enforcement: member cannot edit others' threads
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEditGuards:
    def test_member_cannot_edit_status_on_others_thread(
        self, client, member_user, target_user, thread_general,
    ):
        """Member POSTs to edit_status on others' thread -> 403."""
        thread_general.assigned_to = target_user
        thread_general.save()
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/edit-status/",
            {"new_status": "acknowledged"},
        )
        assert resp.status_code == 403

    def test_member_cannot_edit_priority_on_others_thread(
        self, client, member_user, target_user, thread_general,
    ):
        """Member POSTs to edit_priority on others' thread -> 403."""
        thread_general.assigned_to = target_user
        thread_general.save()
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/edit-priority/",
            {"priority": "HIGH"},
        )
        assert resp.status_code == 403

    def test_member_cannot_edit_category_on_others_thread(
        self, client, member_user, target_user, thread_general,
    ):
        """Member POSTs to edit_category on others' thread -> 403."""
        thread_general.assigned_to = target_user
        thread_general.save()
        client.force_login(member_user)
        resp = client.post(
            f"/emails/threads/{thread_general.pk}/edit-category/",
            {"category": "Sales"},
        )
        assert resp.status_code == 403
