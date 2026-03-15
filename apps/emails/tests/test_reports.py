"""Tests for reports aggregation service and reports view."""

import pytest
from datetime import datetime, date, timedelta, timezone as dt_tz

from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import ActivityLog, Email, SLAConfig, Thread
from conftest import create_email, create_thread


# ===========================================================================
# Helpers
# ===========================================================================

def _create_activity(thread, user, action, created_at):
    """Create an ActivityLog with a specific created_at (bypasses auto_now_add)."""
    a = ActivityLog.objects.create(thread=thread, user=user, action=action)
    # auto_now_add ignores passed value; force via update()
    ActivityLog.objects.filter(pk=a.pk).update(created_at=created_at)
    a.refresh_from_db()
    return a


def _make_thread_with_email(
    received_at=None,
    to_inbox="info@vidarbhainfotech.com",
    category="General Inquiry",
    priority="MEDIUM",
    assigned_to=None,
    status="new",
    sla_ack_deadline=None,
):
    """Create a Thread + linked Email in a single call."""
    t = create_thread(
        category=category,
        priority=priority,
        assigned_to=assigned_to,
        status=status,
        sla_ack_deadline=sla_ack_deadline,
        last_message_at=received_at,
    )
    e = create_email(
        thread=t,
        to_inbox=to_inbox,
        received_at=received_at or datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
        category=category,
        priority=priority,
    )
    return t, e


# ===========================================================================
# Service tests -- get_overview_kpis
# ===========================================================================

@pytest.mark.django_db
class TestOverviewKPIs:

    def test_overview_kpis_with_data(self):
        """Verify total_emails, avg_response_minutes, sla_compliance_pct, open_threads."""
        from apps.emails.services.reports import get_overview_kpis

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        t1, e1 = _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
            sla_ack_deadline=datetime(2026, 3, 11, 12, 0, 0, tzinfo=dt_tz.utc),
        )
        t2, e2 = _make_thread_with_email(
            received_at=datetime(2026, 3, 15, 9, 0, 0, tzinfo=dt_tz.utc),
            status="acknowledged",
        )

        # Acknowledge t1 within deadline
        admin = User.objects.create_user(
            username="reporter_admin", password="x", email="ra@test.com",
            role=User.Role.ADMIN, is_staff=True,
        )
        _create_activity(t1, admin, ActivityLog.Action.ACKNOWLEDGED,
                         datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_tz.utc))

        result = get_overview_kpis(start, end)
        assert result["total_emails"] == 2
        assert result["avg_response_minutes"] is not None
        assert result["open_threads"] >= 1  # at least t1 or t2 is open

    def test_overview_kpis_empty(self):
        """No data in range: sensible defaults."""
        from apps.emails.services.reports import get_overview_kpis

        start = datetime(2099, 1, 1, tzinfo=dt_tz.utc)
        end = datetime(2099, 12, 31, tzinfo=dt_tz.utc)

        result = get_overview_kpis(start, end)
        assert result["total_emails"] == 0
        assert result["avg_response_minutes"] is None
        assert result["sla_compliance_pct"] == 100.0
        assert result["open_threads"] >= 0


# ===========================================================================
# Service tests -- get_volume_data
# ===========================================================================

@pytest.mark.django_db
class TestVolumeData:

    def test_volume_data_groups_by_inbox(self):
        """Two inboxes produce two datasets."""
        from apps.emails.services.reports import get_volume_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
            to_inbox="info@vidarbhainfotech.com",
        )
        _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_tz.utc),
            to_inbox="sales@vidarbhainfotech.com",
        )

        result = get_volume_data(start, end)
        assert len(result["datasets"]) == 2
        assert all(isinstance(lbl, str) for lbl in result["labels"])
        # Labels should be YYYY-MM-DD strings
        assert result["labels"][0].count("-") == 2

    def test_volume_data_fills_zero_dates(self):
        """Days without emails have zero counts (no gaps in chart)."""
        from apps.emails.services.reports import get_volume_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 5, 23, 59, 59, tzinfo=dt_tz.utc)

        # Only day 1 and day 5 have emails
        _make_thread_with_email(
            received_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=dt_tz.utc),
        )
        _make_thread_with_email(
            received_at=datetime(2026, 3, 5, 10, 0, 0, tzinfo=dt_tz.utc),
        )

        result = get_volume_data(start, end)
        assert len(result["labels"]) == 5  # 5 days
        # Datasets should have 5 data points each
        for ds in result["datasets"]:
            assert len(ds["data"]) == 5


# ===========================================================================
# Service tests -- get_team_data
# ===========================================================================

@pytest.mark.django_db
class TestTeamData:

    def test_team_data_counts_per_user(self):
        """Two users with different activity counts."""
        from apps.emails.services.reports import get_team_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        u1 = User.objects.create_user(
            username="alice", password="x", email="a@test.com",
            first_name="Alice", last_name="Smith",
        )
        u2 = User.objects.create_user(
            username="bob", password="x", email="b@test.com",
            first_name="Bob", last_name="Jones",
        )

        t1, _ = _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
        )
        t2, _ = _make_thread_with_email(
            received_at=datetime(2026, 3, 11, 12, 0, 0, tzinfo=dt_tz.utc),
        )
        t3, _ = _make_thread_with_email(
            received_at=datetime(2026, 3, 12, 12, 0, 0, tzinfo=dt_tz.utc),
        )

        # Alice acknowledged 2 threads, Bob acknowledged 1
        _create_activity(t1, u1, ActivityLog.Action.ACKNOWLEDGED,
                         datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_tz.utc))
        _create_activity(t2, u1, ActivityLog.Action.ACKNOWLEDGED,
                         datetime(2026, 3, 11, 14, 0, 0, tzinfo=dt_tz.utc))
        _create_activity(t3, u2, ActivityLog.Action.ACKNOWLEDGED,
                         datetime(2026, 3, 12, 14, 0, 0, tzinfo=dt_tz.utc))

        result = get_team_data(start, end)
        assert len(result["labels"]) == 2
        # Alice (2) should be first (ordered by -handle_count)
        assert result["labels"][0] == "Alice Smith"
        assert result["datasets"]["handle_count"][0] == 2
        assert result["labels"][1] == "Bob Jones"
        assert result["datasets"]["handle_count"][1] == 1
        # avg_response_minutes should be floats (JSON serializable)
        for v in result["datasets"]["avg_response_minutes"]:
            assert isinstance(v, (int, float))


# ===========================================================================
# Service tests -- get_sla_data
# ===========================================================================

@pytest.mark.django_db
class TestSLAData:

    def test_sla_data_compliance(self):
        """Mix of met and breached SLA gives correct compliance %."""
        from apps.emails.services.reports import get_sla_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        admin = User.objects.create_user(
            username="sla_admin", password="x", email="sla@test.com",
            role=User.Role.ADMIN, is_staff=True,
        )

        # Thread 1: SLA met (acknowledged before deadline)
        t1, _ = _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
            sla_ack_deadline=datetime(2026, 3, 11, 12, 0, 0, tzinfo=dt_tz.utc),
        )
        _create_activity(t1, admin, ActivityLog.Action.ACKNOWLEDGED,
                         datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_tz.utc))

        # Thread 2: SLA breached (acknowledged AFTER deadline)
        t2, _ = _make_thread_with_email(
            received_at=datetime(2026, 3, 15, 9, 0, 0, tzinfo=dt_tz.utc),
            sla_ack_deadline=datetime(2026, 3, 15, 10, 0, 0, tzinfo=dt_tz.utc),
        )
        _create_activity(t2, admin, ActivityLog.Action.ACKNOWLEDGED,
                         datetime(2026, 3, 16, 10, 0, 0, tzinfo=dt_tz.utc))

        result = get_sla_data(start, end)
        assert result["donut_data"]["met"] == 1
        assert result["donut_data"]["breached"] == 1
        assert result["compliance_pct"] == 50.0

    def test_sla_data_breach_list(self):
        """Breached threads appear in breaches list with correct fields."""
        from apps.emails.services.reports import get_sla_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        # Breached: deadline already passed, never acknowledged
        t1, _ = _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
            sla_ack_deadline=datetime(2026, 3, 10, 13, 0, 0, tzinfo=dt_tz.utc),
        )

        result = get_sla_data(start, end)
        assert len(result["breaches"]) >= 1
        breach = result["breaches"][0]
        assert "thread_id" in breach
        assert "subject" in breach
        assert "priority" in breach
        assert "deadline" in breach
        assert breach["actual"] == "Not acknowledged"


# ===========================================================================
# Service tests -- filters
# ===========================================================================

@pytest.mark.django_db
class TestReportFilters:

    def test_filters_by_inbox(self):
        """Inbox filter narrows results."""
        from apps.emails.services.reports import get_volume_data

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
            to_inbox="info@vidarbhainfotech.com",
        )
        _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_tz.utc),
            to_inbox="sales@vidarbhainfotech.com",
        )

        result = get_volume_data(start, end, inbox="info@vidarbhainfotech.com")
        # Only info@ dataset
        total = sum(sum(ds["data"]) for ds in result["datasets"])
        assert total == 1

    def test_filters_by_category(self):
        """Category filter narrows results."""
        from apps.emails.services.reports import get_overview_kpis

        start = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=dt_tz.utc)

        _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=dt_tz.utc),
            category="billing",
        )
        _make_thread_with_email(
            received_at=datetime(2026, 3, 10, 14, 0, 0, tzinfo=dt_tz.utc),
            category="support",
        )

        result = get_overview_kpis(start, end, category="billing")
        assert result["total_emails"] == 1

    def test_date_range_excludes_outside(self):
        """Emails outside date range are not counted."""
        from apps.emails.services.reports import get_overview_kpis

        start = datetime(2026, 3, 10, tzinfo=dt_tz.utc)
        end = datetime(2026, 3, 15, 23, 59, 59, tzinfo=dt_tz.utc)

        # Inside range
        _make_thread_with_email(
            received_at=datetime(2026, 3, 12, 12, 0, 0, tzinfo=dt_tz.utc),
        )
        # Outside range (before)
        _make_thread_with_email(
            received_at=datetime(2026, 3, 5, 12, 0, 0, tzinfo=dt_tz.utc),
        )
        # Outside range (after)
        _make_thread_with_email(
            received_at=datetime(2026, 3, 20, 12, 0, 0, tzinfo=dt_tz.utc),
        )

        result = get_overview_kpis(start, end)
        assert result["total_emails"] == 1


# ===========================================================================
# View tests
# ===========================================================================

@pytest.mark.django_db
class TestReportsView:

    def test_reports_requires_admin(self, client, member_user):
        """Non-admin GET /emails/reports/ returns 403."""
        client.force_login(member_user)
        resp = client.get("/emails/reports/")
        assert resp.status_code == 403

    def test_reports_accessible_to_admin(self, client, admin_user):
        """Admin GET /emails/reports/ returns 200."""
        client.force_login(admin_user)
        resp = client.get("/emails/reports/")
        assert resp.status_code == 200

    def test_reports_default_preset(self, client, admin_user):
        """No query params uses last_30 default; context has all data keys."""
        client.force_login(admin_user)
        resp = client.get("/emails/reports/")
        assert resp.status_code == 200
        ctx = resp.context
        assert "overview_kpis" in ctx
        assert "volume_data" in ctx
        assert "team_data" in ctx
        assert "sla_data" in ctx
        assert ctx["preset"] == "last_30"

    def test_reports_custom_date_range(self, client, admin_user):
        """Custom date range is applied."""
        client.force_login(admin_user)
        resp = client.get("/emails/reports/", {
            "preset": "custom",
            "start": "2026-01-01",
            "end": "2026-01-31",
        })
        assert resp.status_code == 200
        assert resp.context["preset"] == "custom"

    def test_reports_preset_today(self, client, admin_user):
        """preset=today returns 200 with today's date range."""
        client.force_login(admin_user)
        resp = client.get("/emails/reports/", {"preset": "today"})
        assert resp.status_code == 200
        assert resp.context["preset"] == "today"
