"""Tests for SpamWhitelist model and bool normalization."""

import importlib
import pytest
from django.db import IntegrityError

from apps.core.models import SystemConfig
from apps.emails.models import SpamWhitelist


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
