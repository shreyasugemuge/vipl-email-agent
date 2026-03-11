"""Tests for SLA calculation, business hours, and breach detection."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from apps.accounts.models import User
from apps.emails.models import Email, SLAConfig


IST = ZoneInfo("Asia/Kolkata")


def _create_email(db, **overrides):
    """Helper to create an Email record."""
    from datetime import timezone

    defaults = {
        "message_id": f"msg_sla_{id(overrides)}",
        "from_address": "sender@example.com",
        "from_name": "Test Sender",
        "to_inbox": "info@vidarbhainfotech.com",
        "subject": "Test Subject",
        "body": "Test body",
        "received_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        "category": "General Inquiry",
        "priority": "MEDIUM",
        "processing_status": Email.ProcessingStatus.COMPLETED,
        "status": Email.Status.NEW,
    }
    defaults.update(overrides)
    return Email.objects.create(**defaults)


# ===========================================================================
# SLA Calculator Tests
# ===========================================================================


@pytest.mark.django_db
class TestSLACalculator:
    """Test calculate_sla_deadline business hours logic."""

    def test_same_day_within_business_hours(self):
        """3 PM Wed + 2 hours = 5 PM Wed."""
        from apps.emails.services.sla import calculate_sla_deadline

        # Wednesday 3 PM IST
        start = datetime(2026, 3, 11, 15, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 2.0)
        expected = datetime(2026, 3, 11, 17, 0, 0, tzinfo=IST)
        assert result == expected

    def test_crosses_overnight(self):
        """7 PM Wed + 2 hours = 10 AM Thu (crosses overnight boundary)."""
        from apps.emails.services.sla import calculate_sla_deadline

        # Wednesday 7 PM IST (1 hour left in biz day)
        start = datetime(2026, 3, 11, 19, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 2.0)
        # 1 hour Wed + 1 hour Thu morning = 9 AM Thu
        expected = datetime(2026, 3, 12, 9, 0, 0, tzinfo=IST)
        assert result == expected

    def test_skips_sunday(self):
        """3 PM Sat + 14 hours = 5 PM Mon (skips Sunday)."""
        from apps.emails.services.sla import calculate_sla_deadline

        # Saturday 3 PM IST, March 14 2026 is a Saturday
        start = datetime(2026, 3, 14, 15, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 14.0)
        # 5 hours left on Sat (15-20) + 12 hours Mon (8-20) = 17 hours
        # Need 14: 5 on Sat + 9 on Mon = 8+9 = 17:00 Mon
        expected = datetime(2026, 3, 16, 17, 0, 0, tzinfo=IST)
        assert result == expected

    def test_outside_hours_snaps_to_next_open(self):
        """11 PM Sat + 1 hour = 9 AM Mon."""
        from apps.emails.services.sla import calculate_sla_deadline

        # Saturday 11 PM IST (outside business hours)
        start = datetime(2026, 3, 14, 23, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 1.0)
        # Snaps to Mon 8 AM + 1 hour = 9 AM Mon
        expected = datetime(2026, 3, 16, 9, 0, 0, tzinfo=IST)
        assert result == expected

    def test_fractional_hours(self):
        """10 AM + 0.5 hours = 10:30 AM."""
        from apps.emails.services.sla import calculate_sla_deadline

        start = datetime(2026, 3, 11, 10, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 0.5)
        expected = datetime(2026, 3, 11, 10, 30, 0, tzinfo=IST)
        assert result == expected

    def test_exactly_at_close(self):
        """8 PM + 1 hour = 9 AM next business day."""
        from apps.emails.services.sla import calculate_sla_deadline

        # Wednesday 8 PM IST (exactly at close)
        start = datetime(2026, 3, 11, 20, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 1.0)
        expected = datetime(2026, 3, 12, 9, 0, 0, tzinfo=IST)
        assert result == expected

    def test_exactly_at_open(self):
        """8 AM + 1 hour = 9 AM same day."""
        from apps.emails.services.sla import calculate_sla_deadline

        start = datetime(2026, 3, 11, 8, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 1.0)
        expected = datetime(2026, 3, 11, 9, 0, 0, tzinfo=IST)
        assert result == expected

    def test_zero_hours(self):
        """0 hours returns snapped start time."""
        from apps.emails.services.sla import calculate_sla_deadline

        start = datetime(2026, 3, 11, 10, 0, 0, tzinfo=IST)
        result = calculate_sla_deadline(start, 0.0)
        assert result == start


# ===========================================================================
# Business Hours Helper Tests
# ===========================================================================


@pytest.mark.django_db
class TestBusinessHours:
    """Test _snap_to_business_hours and _next_business_open."""

    def test_snap_during_business_hours(self):
        """During business hours returns same time."""
        from apps.emails.services.sla import _snap_to_business_hours

        dt = datetime(2026, 3, 11, 14, 0, 0, tzinfo=IST)
        assert _snap_to_business_hours(dt) == dt

    def test_snap_before_open(self):
        """Before open snaps to same day open."""
        from apps.emails.services.sla import _snap_to_business_hours

        dt = datetime(2026, 3, 11, 6, 0, 0, tzinfo=IST)
        expected = datetime(2026, 3, 11, 8, 0, 0, tzinfo=IST)
        assert _snap_to_business_hours(dt) == expected

    def test_snap_after_close(self):
        """After close snaps to next business day open."""
        from apps.emails.services.sla import _snap_to_business_hours

        dt = datetime(2026, 3, 11, 21, 0, 0, tzinfo=IST)
        expected = datetime(2026, 3, 12, 8, 0, 0, tzinfo=IST)
        assert _snap_to_business_hours(dt) == expected

    def test_snap_sunday(self):
        """Sunday snaps to Monday open."""
        from apps.emails.services.sla import _snap_to_business_hours

        # Sunday March 15, 2026
        dt = datetime(2026, 3, 15, 10, 0, 0, tzinfo=IST)
        expected = datetime(2026, 3, 16, 8, 0, 0, tzinfo=IST)
        assert _snap_to_business_hours(dt) == expected

    def test_next_business_open_from_weekday(self):
        """Next business open from a weekday is next day 8 AM."""
        from apps.emails.services.sla import _next_business_open

        dt = datetime(2026, 3, 11, 20, 0, 0, tzinfo=IST)  # Wed
        expected = datetime(2026, 3, 12, 8, 0, 0, tzinfo=IST)
        assert _next_business_open(dt) == expected

    def test_next_business_open_from_saturday(self):
        """Next business open from Saturday is Monday 8 AM."""
        from apps.emails.services.sla import _next_business_open

        dt = datetime(2026, 3, 14, 20, 0, 0, tzinfo=IST)  # Sat
        expected = datetime(2026, 3, 16, 8, 0, 0, tzinfo=IST)
        assert _next_business_open(dt) == expected


# ===========================================================================
# set_sla_deadlines Tests
# ===========================================================================


@pytest.mark.django_db
class TestSetSLADeadlines:
    """Test set_sla_deadlines function."""

    def test_with_sla_config(self):
        """Uses SLAConfig hours when present."""
        from apps.emails.services.sla import set_sla_deadlines

        SLAConfig.objects.create(
            priority="MEDIUM", category="General Inquiry",
            ack_hours=0.5, respond_hours=4.0,
        )
        email = _create_email(
            None,
            message_id="msg_sla_config_1",
            received_at=datetime(2026, 3, 11, 10, 0, 0, tzinfo=IST),
        )
        set_sla_deadlines(email)
        email.refresh_from_db()
        assert email.sla_ack_deadline is not None
        assert email.sla_respond_deadline is not None

    def test_fallback_defaults(self):
        """Uses fallback defaults when no SLAConfig found."""
        from apps.emails.services.sla import set_sla_deadlines

        email = _create_email(
            None,
            message_id="msg_sla_fallback_1",
            priority="HIGH",
            category="Sales Lead",
            received_at=datetime(2026, 3, 11, 10, 0, 0, tzinfo=IST),
        )
        set_sla_deadlines(email)
        email.refresh_from_db()
        assert email.sla_ack_deadline is not None
        assert email.sla_respond_deadline is not None

    def test_noop_for_spam(self):
        """Does not set deadlines for spam emails."""
        from apps.emails.services.sla import set_sla_deadlines

        email = _create_email(
            None,
            message_id="msg_sla_spam_1",
            is_spam=True,
            received_at=datetime(2026, 3, 11, 10, 0, 0, tzinfo=IST),
        )
        set_sla_deadlines(email)
        email.refresh_from_db()
        assert email.sla_ack_deadline is None
        assert email.sla_respond_deadline is None


# ===========================================================================
# Breach Detection Tests
# ===========================================================================


@pytest.mark.django_db
class TestBreachDetection:
    """Test get_breached_emails query."""

    def test_returns_breached_emails(self):
        """Returns emails where now > deadline and not closed."""
        from apps.emails.services.sla import get_breached_emails
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = _create_email(
            None,
            message_id="msg_breach_1",
            sla_respond_deadline=past,
        )
        breached = get_breached_emails(breach_type="respond")
        assert email in breached

    def test_excludes_closed_emails(self):
        """Does not return closed emails even if breached."""
        from apps.emails.services.sla import get_breached_emails
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = _create_email(
            None,
            message_id="msg_breach_2",
            sla_respond_deadline=past,
            status=Email.Status.CLOSED,
        )
        breached = get_breached_emails(breach_type="respond")
        assert email not in breached

    def test_excludes_spam(self):
        """Does not return spam emails."""
        from apps.emails.services.sla import get_breached_emails
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = _create_email(
            None,
            message_id="msg_breach_3",
            sla_respond_deadline=past,
            is_spam=True,
        )
        breached = get_breached_emails(breach_type="respond")
        assert email not in breached

    def test_ack_breach_type(self):
        """breach_type='ack' checks sla_ack_deadline."""
        from apps.emails.services.sla import get_breached_emails
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = _create_email(
            None,
            message_id="msg_breach_4",
            sla_ack_deadline=past,
        )
        breached = get_breached_emails(breach_type="ack")
        assert email in breached
