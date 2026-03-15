"""Tests for SLA calculation, business hours, breach detection, and escalation."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from zoneinfo import ZoneInfo

from apps.accounts.models import User
from apps.emails.models import Email, SLAConfig, ActivityLog
from conftest import create_email


IST = ZoneInfo("Asia/Kolkata")


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
        email = create_email(
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

        email = create_email(
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

        email = create_email(
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
        email = create_email(
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
        email = create_email(
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
        email = create_email(
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
        email = create_email(
            message_id="msg_breach_4",
            sla_ack_deadline=past,
        )
        breached = get_breached_emails(breach_type="ack")
        assert email in breached


# ===========================================================================
# Breach Summary Tests (NEW -- Plan 04-03)
# ===========================================================================


@pytest.mark.django_db
class TestBreachSummary:
    """Test build_breach_summary returns correct structure."""

    def test_summary_structure(self):
        """build_breach_summary returns correct keys and types."""
        from apps.emails.services.sla import build_breach_summary
        from django.utils import timezone as tz

        user = User.objects.create_user(
            username="member1", password="pass", email="m1@vidarbhainfotech.com",
            first_name="Alice", last_name="Dev",
        )
        past = tz.now() - timedelta(hours=3)
        e1 = create_email( message_id="msg_summary_1",
            sla_respond_deadline=past, assigned_to=user, priority="HIGH",
        )

        respond_qs = Email.objects.filter(pk=e1.pk)
        ack_qs = Email.objects.none()

        summary = build_breach_summary(respond_qs, ack_qs)

        assert "total_respond_breached" in summary
        assert "total_ack_breached" in summary
        assert "per_assignee" in summary
        assert "top_offenders" in summary
        assert summary["total_respond_breached"] == 1
        assert summary["total_ack_breached"] == 0

    def test_top_offenders_sorted_by_overdue(self):
        """Top 3 offenders are sorted most-overdue-first."""
        from apps.emails.services.sla import build_breach_summary
        from django.utils import timezone as tz

        user = User.objects.create_user(
            username="member_top", password="pass", email="mt@vidarbhainfotech.com",
        )
        now = tz.now()
        # Create 4 breached emails with different overdue amounts
        emails = []
        for i, hours_overdue in enumerate([1, 5, 2, 10]):
            e = create_email(
                message_id=f"msg_top_{i}",
                sla_respond_deadline=now - timedelta(hours=hours_overdue),
                assigned_to=user,
                priority="HIGH",
                subject=f"Email overdue {hours_overdue}h",
            )
            emails.append(e)

        respond_qs = Email.objects.filter(pk__in=[e.pk for e in emails])
        summary = build_breach_summary(respond_qs, Email.objects.none())

        assert len(summary["top_offenders"]) == 3
        # Most overdue first (10h, 5h, 2h)
        overdue_vals = [o["overdue_minutes"] for o in summary["top_offenders"]]
        assert overdue_vals == sorted(overdue_vals, reverse=True)

    def test_entry_contains_pk(self):
        """build_breach_summary per_assignee entries have 'pk' key matching email.pk."""
        from apps.emails.services.sla import build_breach_summary
        from django.utils import timezone as tz

        user = User.objects.create_user(
            username="member_pk1", password="pass", email="pk1@vidarbhainfotech.com",
            first_name="Pk", last_name="One",
        )
        past = tz.now() - timedelta(hours=2)
        e1 = create_email( message_id="msg_pk_entry_1",
            sla_respond_deadline=past, assigned_to=user, priority="HIGH",
        )

        respond_qs = Email.objects.filter(pk=e1.pk)
        summary = build_breach_summary(respond_qs, Email.objects.none())

        entries = summary["per_assignee"]["Pk One"]
        assert len(entries) == 1
        assert "pk" in entries[0], "Entry should contain 'pk' key"
        assert entries[0]["pk"] == e1.pk

    def test_top_offenders_contain_pk(self):
        """build_breach_summary top_offenders entries have 'pk' key."""
        from apps.emails.services.sla import build_breach_summary
        from django.utils import timezone as tz

        user = User.objects.create_user(
            username="member_pk2", password="pass", email="pk2@vidarbhainfotech.com",
        )
        past = tz.now() - timedelta(hours=3)
        e1 = create_email( message_id="msg_pk_top_1",
            sla_respond_deadline=past, assigned_to=user, priority="HIGH",
        )

        respond_qs = Email.objects.filter(pk=e1.pk)
        summary = build_breach_summary(respond_qs, Email.objects.none())

        assert len(summary["top_offenders"]) >= 1
        for offender in summary["top_offenders"]:
            assert "pk" in offender, "Top offender should contain 'pk' key"
        assert summary["top_offenders"][0]["pk"] == e1.pk

    def test_per_assignee_grouping(self):
        """per_assignee groups breached emails by assignee name."""
        from apps.emails.services.sla import build_breach_summary
        from django.utils import timezone as tz

        u1 = User.objects.create_user(
            username="alice_g", password="pass", first_name="Alice", last_name="G",
        )
        u2 = User.objects.create_user(
            username="bob_g", password="pass", first_name="Bob", last_name="G",
        )
        past = tz.now() - timedelta(hours=2)
        create_email(message_id="msg_grp_1", sla_respond_deadline=past, assigned_to=u1)
        create_email(message_id="msg_grp_2", sla_respond_deadline=past, assigned_to=u1)
        create_email(message_id="msg_grp_3", sla_respond_deadline=past, assigned_to=u2)

        respond_qs = Email.objects.filter(message_id__startswith="msg_grp_")
        summary = build_breach_summary(respond_qs, Email.objects.none())

        assert "Alice G" in summary["per_assignee"]
        assert "Bob G" in summary["per_assignee"]
        assert len(summary["per_assignee"]["Alice G"]) == 2
        assert len(summary["per_assignee"]["Bob G"]) == 1


# ===========================================================================
# Check and Escalate Tests (NEW -- Plan 04-03)
# ===========================================================================


@pytest.mark.django_db
class TestCheckAndEscalate:
    """Test check_and_escalate_breaches priority bumping and activity logging."""

    def test_bumps_medium_to_high(self):
        """MEDIUM priority bumps to HIGH on breach."""
        from apps.emails.services.sla import check_and_escalate_breaches
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = create_email( message_id="msg_esc_1",
            sla_respond_deadline=past, priority="MEDIUM",
        )

        check_and_escalate_breaches(chat_notifier=None)

        email.refresh_from_db()
        assert email.priority == "HIGH"

    def test_critical_stays_critical(self):
        """CRITICAL does not escalate further."""
        from apps.emails.services.sla import check_and_escalate_breaches
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = create_email( message_id="msg_esc_2",
            sla_respond_deadline=past, priority="CRITICAL",
        )

        check_and_escalate_breaches(chat_notifier=None)

        email.refresh_from_db()
        assert email.priority == "CRITICAL"

    def test_skip_rebump_within_24h(self):
        """Does not re-bump if SLA_BREACHED logged within 24 hours."""
        from apps.emails.services.sla import check_and_escalate_breaches
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = create_email( message_id="msg_esc_3",
            sla_respond_deadline=past, priority="MEDIUM",
        )

        # Create a recent SLA_BREACHED log (within 24h)
        ActivityLog.objects.create(
            email=email, user=None,
            action=ActivityLog.Action.SLA_BREACHED,
            detail="Already breached",
        )

        check_and_escalate_breaches(chat_notifier=None)

        email.refresh_from_db()
        # Should remain MEDIUM because it was already breached recently
        assert email.priority == "MEDIUM"

    def test_creates_activity_log_entries(self):
        """Creates PRIORITY_BUMPED and SLA_BREACHED ActivityLog entries."""
        from apps.emails.services.sla import check_and_escalate_breaches
        from django.utils import timezone as tz

        past = tz.now() - timedelta(hours=2)
        email = create_email( message_id="msg_esc_4",
            sla_respond_deadline=past, priority="LOW",
        )

        check_and_escalate_breaches(chat_notifier=None)

        bumped = ActivityLog.objects.filter(
            email=email, action=ActivityLog.Action.PRIORITY_BUMPED,
        )
        breached = ActivityLog.objects.filter(
            email=email, action=ActivityLog.Action.SLA_BREACHED,
        )
        assert bumped.exists()
        assert breached.exists()
        assert "LOW" in bumped.first().detail
        assert "MEDIUM" in bumped.first().detail


# ===========================================================================
# Chat Breach Summary Tests (NEW -- Plan 04-03)
# ===========================================================================


@pytest.mark.django_db
class TestChatBreachSummary:
    """Test ChatNotifier.notify_breach_summary builds correct Cards v2 payload."""

    def test_notify_breach_summary_posts_card(self):
        """notify_breach_summary calls _post with Cards v2 payload."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        summary = {
            "total_respond_breached": 3,
            "total_ack_breached": 1,
            "top_offenders": [
                {"subject": "Urgent ticket", "assignee_name": "Alice", "priority": "HIGH", "overdue_str": "2h 30m", "overdue_minutes": 150},
                {"subject": "Another one", "assignee_name": "Bob", "priority": "MEDIUM", "overdue_str": "1h", "overdue_minutes": 60},
            ],
            "per_assignee": {
                "Alice": [{"subject": "Urgent ticket", "priority": "HIGH", "overdue_minutes": 150}],
                "Bob": [{"subject": "Another one", "priority": "MEDIUM", "overdue_minutes": 60},
                         {"subject": "Third", "priority": "LOW", "overdue_minutes": 30}],
            },
        }

        with patch.object(notifier, "_post", return_value=True) as mock_post:
            with patch.object(notifier, "_is_quiet_hours", return_value=False):
                result = notifier.notify_breach_summary(summary)

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        assert "cardsV2" in payload
        card = payload["cardsV2"][0]["card"]
        # Header should mention breach count
        assert "4" in card["header"]["title"] or "breach" in card["header"]["title"].lower()

    def test_breach_summary_quiet_hours_skipped(self):
        """notify_breach_summary skips during quiet hours."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        with patch.object(notifier, "_post") as mock_post:
            with patch.object(notifier, "_is_quiet_hours", return_value=True):
                result = notifier.notify_breach_summary({"total_respond_breached": 1})

        assert result is False
        mock_post.assert_not_called()


# ===========================================================================
# Chat Personal Breach Tests (NEW -- Plan 04-03)
# ===========================================================================


@pytest.mark.django_db
class TestChatPersonalBreach:
    """Test ChatNotifier.notify_personal_breach per-assignee alert."""

    def test_personal_breach_posts_card(self):
        """notify_personal_breach posts Cards v2 with assignee name and their emails."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        breached_emails = [
            {"subject": "Overdue ticket A", "priority": "HIGH", "overdue_minutes": 120},
            {"subject": "Overdue ticket B", "priority": "MEDIUM", "overdue_minutes": 60},
        ]

        with patch.object(notifier, "_post", return_value=True) as mock_post:
            with patch.object(notifier, "_is_quiet_hours", return_value=False):
                result = notifier.notify_personal_breach("Alice Dev", breached_emails)

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        card = payload["cardsV2"][0]["card"]
        assert "Alice Dev" in card["header"]["title"]
        assert "2" in card["header"]["title"]

    def test_personal_breach_quiet_hours(self):
        """notify_personal_breach skips during quiet hours."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        with patch.object(notifier, "_post") as mock_post:
            with patch.object(notifier, "_is_quiet_hours", return_value=True):
                result = notifier.notify_personal_breach("Alice", [{"subject": "x"}])

        assert result is False
        mock_post.assert_not_called()

    def test_personal_breach_lists_only_their_emails(self):
        """Personal alert contains only the passed emails, not all breaches."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        alice_emails = [
            {"subject": "Alice Ticket", "priority": "HIGH", "overdue_minutes": 90},
        ]

        with patch.object(notifier, "_post", return_value=True) as mock_post:
            with patch.object(notifier, "_is_quiet_hours", return_value=False):
                notifier.notify_personal_breach("Alice", alice_emails)

        payload = mock_post.call_args[0][0]
        card = payload["cardsV2"][0]["card"]
        # Should have 1 email widget in sections
        widgets = card["sections"][0]["widgets"]
        assert len(widgets) == 1


# ===========================================================================
# Breach Notification Flow Tests (NEW -- Plan 04-03)
# ===========================================================================


@pytest.mark.django_db
class TestBreachNotificationFlow:
    """Test check_and_escalate_breaches calls both summary and personal alerts."""

    def test_calls_summary_and_personal_for_each_assignee(self):
        """check_and_escalate_breaches calls notify_breach_summary once and
        notify_personal_breach once per assignee with breaches."""
        from apps.emails.services.sla import check_and_escalate_breaches
        from django.utils import timezone as tz

        u1 = User.objects.create_user(
            username="flow_alice", password="pass", first_name="Alice", last_name="F",
        )
        u2 = User.objects.create_user(
            username="flow_bob", password="pass", first_name="Bob", last_name="F",
        )

        past = tz.now() - timedelta(hours=2)
        create_email(message_id="msg_flow_1", sla_respond_deadline=past, assigned_to=u1, priority="MEDIUM")
        create_email(message_id="msg_flow_2", sla_respond_deadline=past, assigned_to=u2, priority="MEDIUM")

        mock_notifier = MagicMock()
        mock_notifier.notify_breach_summary.return_value = True
        mock_notifier.notify_personal_breach.return_value = True

        check_and_escalate_breaches(chat_notifier=mock_notifier)

        mock_notifier.notify_breach_summary.assert_called_once()
        assert mock_notifier.notify_personal_breach.call_count == 2

    def test_no_notification_when_no_breaches(self):
        """No Chat notifications when no emails are breached."""
        from apps.emails.services.sla import check_and_escalate_breaches

        mock_notifier = MagicMock()
        check_and_escalate_breaches(chat_notifier=mock_notifier)

        mock_notifier.notify_breach_summary.assert_not_called()
        mock_notifier.notify_personal_breach.assert_not_called()
