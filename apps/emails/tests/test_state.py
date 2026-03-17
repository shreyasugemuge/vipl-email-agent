"""Tests for StateManager circuit breaker and EOD dedup."""

from datetime import datetime, timedelta

from apps.emails.services.state import StateManager


class TestRecordFailure:
    def test_increments_counter(self):
        sm = StateManager()
        sm.record_failure()
        assert sm.consecutive_failures == 1

    def test_increments_multiple(self):
        sm = StateManager()
        sm.record_failure()
        sm.record_failure()
        sm.record_failure()
        assert sm.consecutive_failures == 3


class TestResetFailures:
    def test_resets_to_zero(self):
        sm = StateManager()
        sm.record_failure()
        sm.record_failure()
        sm.reset_failures()
        assert sm.consecutive_failures == 0


class TestConsecutiveFailures:
    def test_initial_value_is_zero(self):
        sm = StateManager()
        assert sm.consecutive_failures == 0

    def test_tracks_failures_correctly(self):
        sm = StateManager()
        for _ in range(5):
            sm.record_failure()
        assert sm.consecutive_failures == 5


class TestCanSendEod:
    def test_true_when_never_sent(self):
        sm = StateManager()
        assert sm.can_send_eod() is True

    def test_false_within_10_minutes(self):
        sm = StateManager()
        sm._last_eod_time = datetime.now() - timedelta(minutes=5)
        assert sm.can_send_eod() is False

    def test_true_after_10_minutes(self):
        sm = StateManager()
        sm._last_eod_time = datetime.now() - timedelta(minutes=11)
        assert sm.can_send_eod() is True


class TestRecordEodSent:
    def test_updates_timestamp(self):
        sm = StateManager()
        assert sm._last_eod_time is None
        sm.record_eod_sent()
        assert sm._last_eod_time is not None
        assert (datetime.now() - sm._last_eod_time).total_seconds() < 2


class TestDetectConfigChanges:
    def test_first_call_returns_empty(self):
        sm = StateManager()
        changes = sm.detect_config_changes({"a": "1", "b": "2"})
        assert changes == []

    def test_detects_changed_value(self):
        sm = StateManager()
        sm.detect_config_changes({"a": "1", "b": "2"})
        changes = sm.detect_config_changes({"a": "99", "b": "2"})
        assert len(changes) == 1
        assert changes[0] == {"setting": "a", "old_value": "1", "new_value": "99"}

    def test_detects_added_key(self):
        sm = StateManager()
        sm.detect_config_changes({"a": "1"})
        changes = sm.detect_config_changes({"a": "1", "b": "new"})
        assert len(changes) == 1
        assert changes[0]["setting"] == "b"
        assert changes[0]["old_value"] == ""
        assert changes[0]["new_value"] == "new"

    def test_does_not_detect_removed_key(self):
        # Current implementation only iterates over current keys,
        # so removed keys are not reported as changes.
        sm = StateManager()
        sm.detect_config_changes({"a": "1", "b": "2"})
        changes = sm.detect_config_changes({"a": "1"})
        assert changes == []


class TestMultipleFailuresThenReset:
    def test_failures_then_reset(self):
        sm = StateManager()
        for _ in range(7):
            sm.record_failure()
        assert sm.consecutive_failures == 7
        sm.reset_failures()
        assert sm.consecutive_failures == 0
        sm.record_failure()
        assert sm.consecutive_failures == 1
