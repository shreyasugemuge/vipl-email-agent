"""Tests for mark-irrelevant and revert-irrelevant functionality."""

import pytest
from django.urls import reverse

from apps.emails.models import ActivityLog, Thread

# Import shared factories
from conftest import create_thread


@pytest.mark.django_db
class TestMarkIrrelevantView:
    """Tests for the mark_irrelevant endpoint."""

    def test_gatekeeper_can_mark_irrelevant(self, client, triage_lead_user):
        """Triage lead (gatekeeper) can POST to mark a thread as irrelevant."""
        thread = create_thread()
        client.force_login(triage_lead_user)

        response = client.post(
            reverse("emails:mark_irrelevant", args=[thread.pk]),
            data={"reason": "Not relevant to our business"},
        )
        thread.refresh_from_db()

        assert response.status_code == 200
        assert thread.status == Thread.Status.IRRELEVANT

    def test_admin_can_mark_irrelevant(self, client, admin_user):
        """Admin can mark threads as irrelevant."""
        thread = create_thread()
        client.force_login(admin_user)

        response = client.post(
            reverse("emails:mark_irrelevant", args=[thread.pk]),
            data={"reason": "Spam / marketing"},
        )
        thread.refresh_from_db()

        assert response.status_code == 200
        assert thread.status == Thread.Status.IRRELEVANT

    def test_member_forbidden(self, client, member_user):
        """Regular member cannot mark threads as irrelevant."""
        thread = create_thread()
        client.force_login(member_user)

        response = client.post(
            reverse("emails:mark_irrelevant", args=[thread.pk]),
            data={"reason": "Trying to dismiss"},
        )
        thread.refresh_from_db()

        assert response.status_code == 403
        assert thread.status == Thread.Status.NEW

    def test_empty_reason_rejected(self, client, admin_user):
        """Empty reason is rejected with 403."""
        thread = create_thread()
        client.force_login(admin_user)

        response = client.post(
            reverse("emails:mark_irrelevant", args=[thread.pk]),
            data={"reason": ""},
        )
        thread.refresh_from_db()

        assert response.status_code == 403
        assert thread.status == Thread.Status.NEW

    def test_activity_log_created(self, client, admin_user):
        """ActivityLog entry with MARKED_IRRELEVANT action is created."""
        thread = create_thread(status=Thread.Status.ACKNOWLEDGED)
        client.force_login(admin_user)

        client.post(
            reverse("emails:mark_irrelevant", args=[thread.pk]),
            data={"reason": "Test reason"},
        )

        log = ActivityLog.objects.filter(
            thread=thread, action=ActivityLog.Action.MARKED_IRRELEVANT
        ).first()
        assert log is not None
        assert log.detail == "Test reason"
        assert log.old_value == "acknowledged"
        assert log.new_value == "irrelevant"
        assert log.user == admin_user

    def test_anonymous_redirects(self, client):
        """Anonymous user is redirected to login."""
        thread = create_thread()

        response = client.post(
            reverse("emails:mark_irrelevant", args=[thread.pk]),
            data={"reason": "Some reason"},
        )

        assert response.status_code == 302
        assert "/accounts/login/" in response.url or "/login/" in response.url


@pytest.mark.django_db
class TestRevertIrrelevantView:
    """Tests for the revert_irrelevant endpoint."""

    def test_revert_resets_status(self, client, admin_user):
        """Reverting an irrelevant thread resets to NEW and clears assignment."""
        thread = create_thread(status=Thread.Status.IRRELEVANT)
        thread.assigned_to = admin_user
        thread.assigned_by = admin_user
        thread.save()
        client.force_login(admin_user)

        response = client.post(
            reverse("emails:revert_irrelevant", args=[thread.pk]),
        )
        thread.refresh_from_db()

        assert response.status_code == 200
        assert thread.status == Thread.Status.NEW
        assert thread.assigned_to is None
        assert thread.assigned_by is None
        assert thread.assigned_at is None

    def test_revert_non_irrelevant_rejected(self, client, admin_user):
        """Cannot revert a thread that is not in IRRELEVANT status."""
        thread = create_thread(status=Thread.Status.NEW)
        client.force_login(admin_user)

        response = client.post(
            reverse("emails:revert_irrelevant", args=[thread.pk]),
        )

        assert response.status_code == 403

    def test_revert_activity_log(self, client, admin_user):
        """ActivityLog entry with REVERTED_IRRELEVANT action is created on revert."""
        thread = create_thread(status=Thread.Status.IRRELEVANT)
        client.force_login(admin_user)

        client.post(
            reverse("emails:revert_irrelevant", args=[thread.pk]),
        )

        log = ActivityLog.objects.filter(
            thread=thread, action=ActivityLog.Action.REVERTED_IRRELEVANT
        ).first()
        assert log is not None
        assert log.old_value == "irrelevant"
        assert log.new_value == "new"
        assert log.user == admin_user


@pytest.mark.django_db
class TestIrrelevantFiltering:
    """Tests that irrelevant threads are excluded from default views."""

    def test_irrelevant_excluded_from_default_views(self, client, admin_user):
        """Irrelevant threads do not appear in unassigned, all_open, or mine views."""
        thread = create_thread(status=Thread.Status.IRRELEVANT, subject="Irrelevant Thread XYZ")
        client.force_login(admin_user)

        # Check unassigned view
        response = client.get(reverse("emails:thread_list") + "?view=unassigned")
        assert response.status_code == 200
        assert b"Irrelevant Thread XYZ" not in response.content

        # Check all_open view
        response = client.get(reverse("emails:thread_list") + "?view=all_open")
        assert response.status_code == 200
        assert b"Irrelevant Thread XYZ" not in response.content

        # Check mine view
        response = client.get(reverse("emails:thread_list") + "?view=mine")
        assert response.status_code == 200
        assert b"Irrelevant Thread XYZ" not in response.content

    def test_status_filter_shows_irrelevant(self, client, admin_user):
        """Irrelevant threads appear when ?status=irrelevant filter is used."""
        thread = create_thread(status=Thread.Status.IRRELEVANT, subject="Irrelevant Thread ABC")
        client.force_login(admin_user)

        # Use ?view=closed to get past the open-only view filter,
        # then status=irrelevant overrides to show irrelevant threads
        response = client.get(
            reverse("emails:thread_list") + "?status=irrelevant"
        )
        assert response.status_code == 200
        assert b"Irrelevant Thread ABC" in response.content
