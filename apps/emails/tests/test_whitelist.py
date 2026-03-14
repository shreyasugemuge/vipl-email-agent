"""Tests for SpamWhitelist model, bool normalization, and pipeline whitelist integration."""

import importlib
from unittest.mock import MagicMock

import pytest
from django.db import IntegrityError

from apps.core.models import SystemConfig
from apps.emails.models import SpamWhitelist
from conftest import make_email_message, make_triage_result


def _get_normalize_fn():
    """Import the normalize function from the numbered migration module."""
    mod = importlib.import_module("apps.core.migrations.0005_normalize_bools")
    return mod.normalize_bools_forward


@pytest.mark.django_db
class TestSpamWhitelistModel:
    """Test SpamWhitelist CRUD, soft delete, and constraints."""

    def test_create_email_entry(self, admin_user):
        entry = SpamWhitelist.objects.create(
            entry="john@acme.com",
            entry_type="email",
            added_by=admin_user,
        )
        assert entry.pk is not None
        assert entry.entry == "john@acme.com"
        assert entry.entry_type == "email"
        assert entry.added_by == admin_user

    def test_create_domain_entry(self, admin_user):
        entry = SpamWhitelist.objects.create(
            entry="acme.com",
            entry_type="domain",
            added_by=admin_user,
        )
        assert entry.pk is not None
        assert entry.entry == "acme.com"
        assert entry.entry_type == "domain"

    def test_create_entry_without_user(self, db):
        entry = SpamWhitelist.objects.create(
            entry="test@example.com",
            entry_type="email",
        )
        assert entry.pk is not None
        assert entry.added_by is None

    def test_unique_together_constraint(self, db):
        SpamWhitelist.objects.create(entry="john@acme.com", entry_type="email")
        with pytest.raises(IntegrityError):
            SpamWhitelist.objects.create(entry="john@acme.com", entry_type="email")

    def test_same_entry_different_type_allowed(self, db):
        SpamWhitelist.objects.create(entry="acme.com", entry_type="email")
        SpamWhitelist.objects.create(entry="acme.com", entry_type="domain")
        assert SpamWhitelist.objects.count() == 2

    def test_soft_delete(self, db):
        entry = SpamWhitelist.objects.create(entry="john@acme.com", entry_type="email")
        entry.delete()
        # Excluded from default queryset
        assert SpamWhitelist.objects.count() == 0
        # Still in all_objects
        assert SpamWhitelist.all_objects.count() == 1
        entry.refresh_from_db()
        assert entry.deleted_at is not None

    def test_str_representation(self, db):
        entry = SpamWhitelist.objects.create(entry="john@acme.com", entry_type="email")
        assert str(entry) == "john@acme.com (email)"

    def test_str_representation_domain(self, db):
        entry = SpamWhitelist.objects.create(entry="acme.com", entry_type="domain")
        assert str(entry) == "acme.com (domain)"

    def test_reason_field(self, db):
        entry = SpamWhitelist.objects.create(
            entry="vip@client.com",
            entry_type="email",
            reason="VIP client, never filter",
        )
        assert entry.reason == "VIP client, never filter"

    def test_ordering_by_created_at_desc(self, db):
        e1 = SpamWhitelist.objects.create(entry="first@example.com", entry_type="email")
        e2 = SpamWhitelist.objects.create(entry="second@example.com", entry_type="email")
        entries = list(SpamWhitelist.objects.all())
        assert entries[0] == e2  # Most recent first
        assert entries[1] == e1


@pytest.mark.django_db
class TestBoolNormalization:
    """Test bool normalization logic (data migration function)."""

    def test_normalize_true_to_lowercase(self, db):
        normalize = _get_normalize_fn()
        SystemConfig.objects.create(key="test_true", value="True", value_type="bool")
        normalize(SystemConfig)
        cfg = SystemConfig.objects.get(key="test_true")
        assert cfg.value == "true"

    def test_normalize_false_to_lowercase(self, db):
        normalize = _get_normalize_fn()
        SystemConfig.objects.create(key="test_false", value="FALSE", value_type="bool")
        normalize(SystemConfig)
        cfg = SystemConfig.objects.get(key="test_false")
        assert cfg.value == "false"

    def test_normalize_yes_to_true(self, db):
        normalize = _get_normalize_fn()
        SystemConfig.objects.create(key="test_yes", value="Yes", value_type="bool")
        normalize(SystemConfig)
        cfg = SystemConfig.objects.get(key="test_yes")
        assert cfg.value == "true"

    def test_normalize_no_to_false(self, db):
        normalize = _get_normalize_fn()
        SystemConfig.objects.create(key="test_no", value="No", value_type="bool")
        normalize(SystemConfig)
        cfg = SystemConfig.objects.get(key="test_no")
        assert cfg.value == "false"

    def test_already_lowercase_unchanged(self, db):
        normalize = _get_normalize_fn()
        SystemConfig.objects.create(key="test_ok", value="true", value_type="bool")
        normalize(SystemConfig)
        cfg = SystemConfig.objects.get(key="test_ok")
        assert cfg.value == "true"

    def test_non_bool_type_untouched(self, db):
        normalize = _get_normalize_fn()
        SystemConfig.objects.create(key="test_str", value="True", value_type="str")
        normalize(SystemConfig)
        cfg = SystemConfig.objects.get(key="test_str")
        assert cfg.value == "True"  # Untouched


@pytest.mark.django_db
class TestWhitelistPipelineIntegration:
    """Test whitelist check in the pipeline (process_single_email)."""

    def test_whitelisted_email_bypasses_spam_filter(self, db):
        """Whitelisted email sender skips spam_filter_fn."""
        from apps.emails.services.pipeline import process_single_email

        SpamWhitelist.objects.create(entry="trusted@acme.com", entry_type="email")

        email_msg = make_email_message(
            message_id="wl_email_001",
            sender_email="trusted@acme.com",
            subject="Unsubscribe from this list",  # Would match spam regex
        )
        triage = make_triage_result()
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn,
            ai_enabled=True, chat_enabled=False,
        )

        # Spam filter should NOT have been called
        mock_spam_fn.assert_not_called()
        # AI should have been called
        mock_ai.process.assert_called_once()
        assert result is not None

    def test_whitelisted_domain_bypasses_spam_filter(self, db):
        """Whitelisted domain sender skips spam_filter_fn."""
        from apps.emails.services.pipeline import process_single_email

        SpamWhitelist.objects.create(entry="acme.com", entry_type="domain")

        email_msg = make_email_message(
            message_id="wl_domain_001",
            sender_email="anyone@acme.com",
            subject="Unsubscribe from this list",
        )
        triage = make_triage_result()
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn,
            ai_enabled=True, chat_enabled=False,
        )

        mock_spam_fn.assert_not_called()
        mock_ai.process.assert_called_once()
        assert result is not None

    def test_whitelisted_sender_still_gets_ai_triage(self, db):
        """Whitelisted sender always goes through AI triage."""
        from apps.emails.services.pipeline import process_single_email

        SpamWhitelist.objects.create(entry="trusted@acme.com", entry_type="email")

        email_msg = make_email_message(
            message_id="wl_ai_001",
            sender_email="trusted@acme.com",
        )
        triage = make_triage_result(category="Sales Lead", priority="HIGH")
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn,
            ai_enabled=True, chat_enabled=False,
        )

        mock_ai.process.assert_called_once()
        assert result.category == "Sales Lead"

    def test_non_whitelisted_goes_through_spam_filter(self, db):
        """Non-whitelisted sender goes through spam_filter_fn normally."""
        from apps.emails.services.pipeline import process_single_email

        # No whitelist entries at all
        email_msg = make_email_message(
            message_id="nwl_001",
            sender_email="random@unknown.com",
        )
        triage = make_triage_result()
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn,
            ai_enabled=True, chat_enabled=False,
        )

        mock_spam_fn.assert_called_once()

    def test_case_insensitive_email_match(self, db):
        """Whitelist matching is case-insensitive."""
        from apps.emails.services.pipeline import process_single_email

        SpamWhitelist.objects.create(entry="john@acme.com", entry_type="email")

        email_msg = make_email_message(
            message_id="wl_case_001",
            sender_email="John@Acme.Com",
        )
        triage = make_triage_result()
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn,
            ai_enabled=True, chat_enabled=False,
        )

        mock_spam_fn.assert_not_called()

    def test_case_insensitive_domain_match(self, db):
        """Domain whitelist matching is case-insensitive."""
        from apps.emails.services.pipeline import process_single_email

        SpamWhitelist.objects.create(entry="acme.com", entry_type="domain")

        email_msg = make_email_message(
            message_id="wl_domain_case_001",
            sender_email="John@ACME.COM",
        )
        triage = make_triage_result()
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()
        mock_spam_fn = MagicMock(return_value=None)

        result = process_single_email(
            email_msg, mock_ai, mock_poller, mock_spam_fn,
            ai_enabled=True, chat_enabled=False,
        )

        mock_spam_fn.assert_not_called()

    def test_whitelisted_spammy_email_not_marked_spam(self, db):
        """A whitelisted sender whose email matches spam patterns is NOT marked spam."""
        from apps.emails.services.pipeline import process_single_email
        from apps.emails.services.spam_filter import is_spam

        SpamWhitelist.objects.create(entry="trusted@acme.com", entry_type="email")

        email_msg = make_email_message(
            message_id="wl_spammy_001",
            sender_email="trusted@acme.com",
            subject="Click here to opt out now",  # Matches spam regex
            body="Unsubscribe from this mailing list",
        )

        # Verify this WOULD match spam filter if not whitelisted
        assert is_spam(email_msg) is not None

        triage = make_triage_result(is_spam=False, spam_score=0.0)
        mock_ai = MagicMock()
        mock_ai.process.return_value = triage
        mock_poller = MagicMock()

        # Use real spam filter -- but it should be skipped due to whitelist
        result = process_single_email(
            email_msg, mock_ai, mock_poller, is_spam,
            ai_enabled=True, chat_enabled=False,
        )

        # Should NOT be marked as spam
        assert result.is_spam is False
        # AI should have been called
        mock_ai.process.assert_called_once()
