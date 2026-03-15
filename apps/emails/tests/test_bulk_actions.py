"""Tests for bulk action endpoints: bulk_assign, bulk_mark_irrelevant, bulk_undo."""

import json

import pytest
from django.urls import reverse

from apps.emails.models import ActivityLog, Thread
from conftest import create_email, create_thread


@pytest.fixture
def target_user(db):
    """A user to assign threads to."""
    from apps.accounts.models import User

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
def three_threads(db):
    """Create 3 threads, each with one email."""
    threads = []
    for i in range(3):
        t = create_thread(subject=f"Thread {i+1}", status="new")
        create_email(thread=t, gmail_thread_id=t.gmail_thread_id)
        threads.append(t)
    return threads


# ---------------------------------------------------------------------------
# bulk_assign permission + validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bulk_assign_returns_403_for_member(client, member_user, three_threads):
    client.force_login(member_user)
    resp = client.post(
        reverse("emails:bulk_assign"),
        {"thread_ids": [three_threads[0].pk], "assignee_id": member_user.pk},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_bulk_assign_returns_400_when_thread_ids_missing(client, admin_user):
    client.force_login(admin_user)
    resp = client.post(reverse("emails:bulk_assign"), {"assignee_id": admin_user.pk})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_bulk_assign_returns_400_when_assignee_missing(client, admin_user, three_threads):
    client.force_login(admin_user)
    resp = client.post(
        reverse("emails:bulk_assign"),
        {"thread_ids": [three_threads[0].pk]},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# bulk_assign success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bulk_assign_assigns_3_threads(client, admin_user, target_user, three_threads):
    client.force_login(admin_user)
    thread_ids = [t.pk for t in three_threads]
    resp = client.post(
        reverse("emails:bulk_assign"),
        {"thread_ids": thread_ids, "assignee_id": target_user.pk},
    )
    assert resp.status_code == 200

    for t in three_threads:
        t.refresh_from_db()
        assert t.assigned_to == target_user
        assert t.assigned_by == admin_user

    # ActivityLog entry per thread
    logs = ActivityLog.objects.filter(action=ActivityLog.Action.ASSIGNED)
    assert logs.count() == 3
    for log in logs:
        assert "Bulk assigned" in log.detail


@pytest.mark.django_db
def test_bulk_assign_returns_hx_trigger(client, admin_user, target_user, three_threads):
    client.force_login(admin_user)
    resp = client.post(
        reverse("emails:bulk_assign"),
        {"thread_ids": [three_threads[0].pk], "assignee_id": target_user.pk},
    )
    assert resp.status_code == 200
    trigger = json.loads(resp["HX-Trigger"])
    assert "showUndoToast" in trigger
    data = trigger["showUndoToast"]
    assert data["action_type"] == "assign"
    assert len(data["previous_states"]) == 1


# ---------------------------------------------------------------------------
# bulk_mark_irrelevant permission + validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bulk_mark_irrelevant_returns_403_for_member(client, member_user, three_threads):
    client.force_login(member_user)
    resp = client.post(
        reverse("emails:bulk_mark_irrelevant"),
        {"thread_ids": [three_threads[0].pk], "reason": "spam"},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_bulk_mark_irrelevant_returns_400_when_reason_empty(client, admin_user, three_threads):
    client.force_login(admin_user)
    resp = client.post(
        reverse("emails:bulk_mark_irrelevant"),
        {"thread_ids": [three_threads[0].pk], "reason": ""},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# bulk_mark_irrelevant success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bulk_mark_irrelevant_sets_status(client, admin_user, three_threads):
    client.force_login(admin_user)
    thread_ids = [t.pk for t in three_threads]
    resp = client.post(
        reverse("emails:bulk_mark_irrelevant"),
        {"thread_ids": thread_ids, "reason": "Not relevant to us"},
    )
    assert resp.status_code == 200

    for t in three_threads:
        t.refresh_from_db()
        assert t.status == "irrelevant"

    logs = ActivityLog.objects.filter(action=ActivityLog.Action.CLOSED)
    assert logs.count() == 3
    for log in logs:
        assert "Bulk marked irrelevant" in log.detail


# ---------------------------------------------------------------------------
# bulk_undo
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bulk_undo_reverses_assign(client, admin_user, target_user, three_threads):
    """Undo should restore previous assigned_to state."""
    client.force_login(admin_user)
    thread_ids = [t.pk for t in three_threads]

    # First bulk assign
    client.post(
        reverse("emails:bulk_assign"),
        {"thread_ids": thread_ids, "assignee_id": target_user.pk},
    )

    # Build previous_states (all were unassigned, status=new)
    previous_states = [
        {"thread_id": t.pk, "assigned_to_id": None, "status": "new"}
        for t in three_threads
    ]

    resp = client.post(
        reverse("emails:bulk_undo"),
        {"previous_states": json.dumps(previous_states)},
    )
    assert resp.status_code == 200

    for t in three_threads:
        t.refresh_from_db()
        assert t.assigned_to is None
        assert t.status == "new"


@pytest.mark.django_db
def test_bulk_undo_reverses_mark_irrelevant(client, admin_user, three_threads):
    """Undo should restore previous status after bulk mark-irrelevant."""
    client.force_login(admin_user)
    thread_ids = [t.pk for t in three_threads]

    # First bulk mark irrelevant
    client.post(
        reverse("emails:bulk_mark_irrelevant"),
        {"thread_ids": thread_ids, "reason": "Not relevant"},
    )

    previous_states = [
        {"thread_id": t.pk, "status": "new", "assigned_to_id": None}
        for t in three_threads
    ]

    resp = client.post(
        reverse("emails:bulk_undo"),
        {"previous_states": json.dumps(previous_states)},
    )
    assert resp.status_code == 200

    for t in three_threads:
        t.refresh_from_db()
        assert t.status == "new"


# ---------------------------------------------------------------------------
# Triage lead can also use bulk actions (has can_assign)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_triage_lead_can_bulk_assign(client, triage_lead_user, target_user, three_threads):
    """Triage lead has can_assign permission and should be able to bulk assign."""
    client.force_login(triage_lead_user)
    # Need assignment rule for triage lead to see threads
    from apps.emails.models import AssignmentRule
    AssignmentRule.objects.create(
        category="General Inquiry", assignee=triage_lead_user, priority_order=0
    )

    resp = client.post(
        reverse("emails:bulk_assign"),
        {"thread_ids": [three_threads[0].pk], "assignee_id": target_user.pk},
    )
    assert resp.status_code == 200
