"""Tests for unassigned count alert system -- rising-edge detection, cooldown, Chat notification."""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.utils import timezone

from apps.core.models import SystemConfig
from apps.emails.models import Thread
from conftest import create_thread


def _set_config(key, value, value_type="str", category="alerts"):
    """Helper to set a SystemConfig key."""
    SystemConfig.objects.update_or_create(
        key=key,
        defaults={"value": str(value), "value_type": value_type, "category": category},
    )


def _seed_alert_configs(threshold=5, cooldown=30, was_below="true", last_alert_at=""):
    """Seed all alert-related SystemConfig keys."""
    _set_config("unassigned_alert_threshold", threshold, "int")
    _set_config("unassigned_alert_cooldown_minutes", cooldown, "int")
    _set_config("_unassigned_was_below_threshold", was_below)
    _set_config("last_unassigned_alert_at", last_alert_at)


def _create_unassigned_threads(count):
    """Create N unassigned threads with status=new."""
    threads = []
    for i in range(count):
        threads.append(create_thread(status="new", assigned_to=None))
    return threads


@pytest.mark.django_db
class TestCheckUnassignedAlert:
    """Tests for _check_unassigned_alert() rising-edge logic."""

    def test_disabled_when_threshold_is_zero(self):
        """Alert does nothing when threshold is 0 (alerts disabled)."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        _seed_alert_configs(threshold=0)
        _create_unassigned_threads(10)

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post") as mock_post:
            _check_unassigned_alert()
            mock_post.assert_not_called()

    def test_disabled_when_threshold_not_set(self):
        """Alert does nothing when threshold config key does not exist."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        # Remove seeded config so key doesn't exist
        SystemConfig.objects.filter(key="unassigned_alert_threshold").delete()
        _create_unassigned_threads(10)

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post") as mock_post:
            _check_unassigned_alert()
            mock_post.assert_not_called()

    def test_no_alert_below_threshold(self):
        """No alert when unassigned count is below threshold."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        _seed_alert_configs(threshold=5)
        _create_unassigned_threads(3)  # Below threshold

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post") as mock_post:
            _check_unassigned_alert()
            mock_post.assert_not_called()

    def test_rising_edge_fires_alert(self):
        """Alert fires when count crosses threshold upward (was below, now at/above)."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        _seed_alert_configs(threshold=5, was_below="true")
        _create_unassigned_threads(5)  # At threshold

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post", return_value=True) as mock_post:
            with patch.dict("os.environ", {"GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test"}):
                _check_unassigned_alert()
                mock_post.assert_called_once()

        # Verify was_below flag is now "false"
        SystemConfig.invalidate_cache()
        flag = SystemConfig.objects.get(key="_unassigned_was_below_threshold")
        assert flag.value == "false"

    def test_no_refire_when_above_threshold(self):
        """Alert does NOT re-fire when count stays above threshold (rising-edge)."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        _seed_alert_configs(threshold=5, was_below="false")  # Already above
        _create_unassigned_threads(7)

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post") as mock_post:
            with patch.dict("os.environ", {"GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test"}):
                _check_unassigned_alert()
                mock_post.assert_not_called()

    def test_reset_when_drops_below_threshold(self):
        """Flag resets when count drops below threshold."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        _seed_alert_configs(threshold=5, was_below="false")  # Was above
        _create_unassigned_threads(3)  # Now below

        _check_unassigned_alert()

        SystemConfig.invalidate_cache()
        flag = SystemConfig.objects.get(key="_unassigned_was_below_threshold")
        assert flag.value == "true"

    def test_cooldown_respected(self):
        """No alert within cooldown window even on rising edge."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        recent_time = (timezone.now() - timedelta(minutes=10)).isoformat()
        _seed_alert_configs(threshold=5, cooldown=30, was_below="true", last_alert_at=recent_time)
        _create_unassigned_threads(6)

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post") as mock_post:
            with patch.dict("os.environ", {"GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test"}):
                _check_unassigned_alert()
                mock_post.assert_not_called()

    def test_cooldown_expired_allows_alert(self):
        """Alert fires when cooldown has expired."""
        from apps.emails.management.commands.run_scheduler import _check_unassigned_alert

        old_time = (timezone.now() - timedelta(minutes=60)).isoformat()
        _seed_alert_configs(threshold=5, cooldown=30, was_below="true", last_alert_at=old_time)
        _create_unassigned_threads(6)

        with patch("apps.emails.services.chat_notifier.ChatNotifier._post", return_value=True) as mock_post:
            with patch.dict("os.environ", {"GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test"}):
                _check_unassigned_alert()
                mock_post.assert_called_once()


@pytest.mark.django_db
class TestNotifyUnassignedAlert:
    """Tests for ChatNotifier.notify_unassigned_alert() card payload."""

    def test_card_payload_structure(self):
        """Card contains count, threshold, breakdown, and triage queue link."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        breakdown = [
            {"category": "Sales", "count": 3},
            {"category": "Support", "count": 2},
        ]

        with patch.object(notifier, "_post", return_value=True) as mock_post:
            result = notifier.notify_unassigned_alert(5, 5, category_breakdown=breakdown)

        assert result is True
        mock_post.assert_called_once()

        payload = mock_post.call_args[0][0]
        card = payload["cardsV2"][0]["card"]

        # Check header contains count and threshold
        assert "5" in card["header"]["title"]
        assert "5" in card["header"]["title"]

        # Check triage queue link
        card_str = str(card)
        assert "view=unassigned" in card_str

    def test_card_includes_breakdown_text(self):
        """Card subtitle or section includes category breakdown."""
        from apps.emails.services.chat_notifier import ChatNotifier

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        breakdown = [
            {"category": "Sales", "count": 3},
            {"category": "General Inquiry", "count": 2},
        ]

        with patch.object(notifier, "_post", return_value=True) as mock_post:
            notifier.notify_unassigned_alert(5, 5, category_breakdown=breakdown)

        payload = mock_post.call_args[0][0]
        card_str = str(payload)
        assert "Sales" in card_str


@pytest.mark.django_db
class TestHeartbeatIntegration:
    """Test that _heartbeat_job calls _check_unassigned_alert."""

    def test_heartbeat_calls_check_unassigned_alert(self):
        """_heartbeat_job invokes _check_unassigned_alert."""
        with patch("apps.emails.management.commands.run_scheduler._check_unassigned_alert") as mock_check:
            from apps.emails.management.commands.run_scheduler import _heartbeat_job

            _heartbeat_job()
            mock_check.assert_called_once()
