"""Tests for the EOD Reporter service."""

from datetime import timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.utils import timezone

from apps.emails.services.state import StateManager


@pytest.fixture
def state_manager():
    return StateManager()


@pytest.fixture
def chat_notifier():
    notifier = MagicMock()
    notifier.notify_eod_summary.return_value = True
    return notifier


@pytest.fixture
def eod_reporter(chat_notifier, state_manager):
    from apps.emails.services.eod_reporter import EODReporter

    return EODReporter(
        chat_notifier=chat_notifier,
        state_manager=state_manager,
        service_account_key_path="/tmp/fake-sa.json",
        sender_email="admin@vidarbhainfotech.com",
    )


def _create_emails(db):
    """Create 5 test emails with varied statuses/priorities."""
    from apps.emails.models import Email

    now = timezone.now()
    emails = []

    emails.append(Email.objects.create(
        message_id="msg-eod-1",
        from_address="a@test.com",
        to_inbox="info@vidarbhainfotech.com",
        subject="New email 1",
        received_at=now - timedelta(hours=2),
        priority="HIGH",
        category="Technical Support",
        status=Email.Status.NEW,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    ))
    emails.append(Email.objects.create(
        message_id="msg-eod-2",
        from_address="b@test.com",
        to_inbox="info@vidarbhainfotech.com",
        subject="Closed email",
        received_at=now - timedelta(hours=3),
        priority="MEDIUM",
        category="General Inquiry",
        status=Email.Status.CLOSED,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    ))
    emails.append(Email.objects.create(
        message_id="msg-eod-3",
        from_address="c@test.com",
        to_inbox="sales@vidarbhainfotech.com",
        subject="Acknowledged email",
        received_at=now - timedelta(hours=1),
        priority="CRITICAL",
        category="Billing & Payments",
        status=Email.Status.ACKNOWLEDGED,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    ))
    emails.append(Email.objects.create(
        message_id="msg-eod-4",
        from_address="d@test.com",
        to_inbox="info@vidarbhainfotech.com",
        subject="SLA breached email",
        received_at=now - timedelta(hours=5),
        priority="HIGH",
        category="Technical Support",
        status=Email.Status.NEW,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
        sla_respond_deadline=now - timedelta(hours=1),  # breached
    ))
    emails.append(Email.objects.create(
        message_id="msg-eod-5",
        from_address="e@test.com",
        to_inbox="info@vidarbhainfotech.com",
        subject="Spam email",
        received_at=now - timedelta(hours=1),
        priority="LOW",
        category="Spam",
        status=Email.Status.NEW,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=True,
    ))

    return emails


@pytest.mark.django_db
class TestGenerateStats:
    def test_generate_stats(self, eod_reporter):
        """With 5 emails (various statuses/priorities), generate_stats returns correct counts."""
        _create_emails(db=True)

        stats = eod_reporter.generate_stats()

        # 4 non-spam completed emails received today
        assert stats["received_today"] == 4
        assert stats["closed_today"] == 1
        # Open = NEW + ACKNOWLEDGED (not closed, not spam) = 3
        assert stats["total_open"] == 3
        # Unassigned = open emails with no assigned_to = 3
        assert stats["unassigned"] == 3
        # SLA breaches = 1 (msg-eod-4 has expired sla_respond_deadline)
        assert stats["sla_breaches"] == 1
        # Priority breakdown
        assert stats["by_priority"]["HIGH"] == 2
        assert stats["by_priority"]["CRITICAL"] == 1
        assert stats["by_priority"]["MEDIUM"] == 1
        # Category breakdown
        assert stats["by_category"]["Technical Support"] == 2
        assert stats["by_category"]["General Inquiry"] == 1

    def test_generate_stats_empty(self, eod_reporter):
        """With no emails, returns zero counts without crashing."""
        stats = eod_reporter.generate_stats()

        assert stats["received_today"] == 0
        assert stats["closed_today"] == 0
        assert stats["total_open"] == 0
        assert stats["unassigned"] == 0
        assert stats["sla_breaches"] == 0
        assert stats["by_priority"] == {}
        assert stats["by_category"] == {}


@pytest.mark.django_db
class TestRenderEmail:
    def test_render_email(self, eod_reporter):
        """render_email produces HTML string containing key stats values."""
        _create_emails(db=True)
        stats = eod_reporter.generate_stats()
        html = eod_reporter.render_email(stats)

        assert isinstance(html, str)
        assert "Daily Summary" in html
        assert str(stats["received_today"]) in html
        assert str(stats["total_open"]) in html


@pytest.mark.django_db
class TestSendReport:
    def test_send_report_respects_eod_flag(self, eod_reporter, chat_notifier):
        """With eod_email_enabled=False, email is NOT sent."""
        from apps.core.models import SystemConfig

        SystemConfig.objects.update_or_create(
            key="eod_email_enabled",
            defaults={"value": "false", "value_type": "bool"},
        )
        SystemConfig.objects.update_or_create(
            key="chat_notifications_enabled",
            defaults={"value": "true", "value_type": "bool"},
        )

        with patch.object(eod_reporter, "_send_email") as mock_send:
            eod_reporter.send_report()
            mock_send.assert_not_called()

        # Chat should still be called
        chat_notifier.notify_eod_summary.assert_called_once()

    def test_send_report_respects_chat_flag(self, eod_reporter, chat_notifier):
        """With chat_notifications_enabled=False, Chat is NOT posted."""
        from apps.core.models import SystemConfig

        SystemConfig.objects.update_or_create(
            key="chat_notifications_enabled",
            defaults={"value": "false", "value_type": "bool"},
        )
        SystemConfig.objects.update_or_create(
            key="eod_email_enabled",
            defaults={"value": "true", "value_type": "bool"},
        )

        with patch.object(eod_reporter, "_send_email"):
            eod_reporter.send_report()

        chat_notifier.notify_eod_summary.assert_not_called()

    def test_send_report_dedup(self, eod_reporter, chat_notifier):
        """Calling send_report twice within 10 min -- second call is skipped."""
        from apps.core.models import SystemConfig

        SystemConfig.objects.update_or_create(
            key="chat_notifications_enabled",
            defaults={"value": "true", "value_type": "bool"},
        )
        SystemConfig.objects.update_or_create(
            key="eod_email_enabled",
            defaults={"value": "false", "value_type": "bool"},
        )

        with patch.object(eod_reporter, "_send_email"):
            eod_reporter.send_report()  # first call
            eod_reporter.send_report()  # second call -- should be skipped

        # Chat should only be called once (dedup blocks second)
        assert chat_notifier.notify_eod_summary.call_count == 1


@pytest.mark.django_db
class TestNotifyEodSummary:
    def test_notify_eod_summary(self):
        """ChatNotifier.notify_eod_summary posts Cards v2 payload with stats."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        stats = {
            "date": "12 Mar 2026",
            "received_today": 10,
            "closed_today": 3,
            "total_open": 7,
            "unassigned": 2,
            "sla_breaches": 1,
            "by_priority": {"HIGH": 4, "MEDIUM": 6},
            "by_category": {"Technical Support": 5, "General Inquiry": 5},
            "avg_time_to_acknowledge": "1h 30m",
            "avg_time_to_respond": "4h 15m",
            "worst_overdue": [],
        }

        with patch.object(notifier, "_is_quiet_hours", return_value=False):
            with patch.object(notifier, "_post", return_value=True) as mock_post:
                result = notifier.notify_eod_summary(stats)

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[0][0]
        assert "cardsV2" in payload
        card = payload["cardsV2"][0]["card"]
        assert "Daily Summary" in card["header"]["title"]

    def test_notify_eod_summary_quiet_hours(self):
        """During quiet hours, Chat card is NOT posted."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        stats = {"date": "12 Mar 2026", "received_today": 5}

        with patch.object(notifier, "_is_quiet_hours", return_value=True):
            with patch.object(notifier, "_post") as mock_post:
                result = notifier.notify_eod_summary(stats)

        assert result is False
        mock_post.assert_not_called()
