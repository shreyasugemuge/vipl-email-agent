"""Tests for settings views, claim endpoint, AI suggestion endpoints, and whitelist."""

import pytest
from datetime import datetime, timezone, timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone as dj_timezone

from apps.accounts.models import User
from apps.core.models import SystemConfig
from apps.emails.models import (
    AssignmentRule, CategoryVisibility, Email, SLAConfig, SpamWhitelist,
)
from conftest import create_email, create_thread


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.login(username="admin", password="testpass123")
    return c


@pytest.fixture
def member_client(member_user):
    c = Client()
    c.login(username="member", password="testpass123")
    return c


@pytest.fixture
def second_member(db):
    return User.objects.create_user(
        username="member2",
        password="testpass123",
        email="member2@vidarbhainfotech.com",
        role=User.Role.MEMBER,
    )


# ---------------------------------------------------------------------------
# Settings page access
# ---------------------------------------------------------------------------


class TestSettingsView:
    def test_admin_can_access_settings(self, admin_client, db):
        response = admin_client.get(reverse("emails:settings"))
        assert response.status_code == 200

    def test_non_admin_gets_403(self, member_client, db):
        response = member_client.get(reverse("emails:settings"))
        assert response.status_code == 403

    def test_settings_renders_with_existing_data(self, admin_client, admin_user, db):
        # Create some data
        AssignmentRule.objects.create(
            category="Sales Lead", assignee=admin_user, priority_order=0,
        )
        SLAConfig.objects.create(
            priority="CRITICAL", category="Sales Lead", ack_hours=0.5, respond_hours=2.0,
        )
        response = admin_client.get(reverse("emails:settings"))
        assert response.status_code == 200
        content = response.content.decode()
        assert "Sales Lead" in content
        assert "Assignment Rules" in content


# ---------------------------------------------------------------------------
# Assignment rules CRUD
# ---------------------------------------------------------------------------


class TestAssignmentRulesView:
    def test_add_rule(self, admin_client, admin_user, second_member, db):
        response = admin_client.post(
            reverse("emails:settings_rules_save"),
            {"action": "add", "category": "Sales Lead", "assignee_id": second_member.pk},
        )
        assert response.status_code == 200
        assert AssignmentRule.objects.filter(
            category="Sales Lead", assignee=second_member,
        ).exists()

    def test_remove_rule(self, admin_client, admin_user, second_member, db):
        AssignmentRule.objects.create(
            category="Sales Lead", assignee=second_member, priority_order=0,
        )
        response = admin_client.post(
            reverse("emails:settings_rules_save"),
            {"action": "remove", "category": "Sales Lead", "assignee_id": second_member.pk},
        )
        assert response.status_code == 200
        assert not AssignmentRule.objects.filter(
            category="Sales Lead", assignee=second_member,
        ).exists()

    def test_reorder_rules(self, admin_client, admin_user, second_member, db):
        r1 = AssignmentRule.objects.create(
            category="Sales Lead", assignee=admin_user, priority_order=0,
        )
        r2 = AssignmentRule.objects.create(
            category="Sales Lead", assignee=second_member, priority_order=1,
        )
        # Reorder: second_member first, then admin_user
        response = admin_client.post(
            reverse("emails:settings_rules_save"),
            {
                "action": "reorder",
                "category": "Sales Lead",
                "assignee_ids[]": [second_member.pk, admin_user.pk],
            },
        )
        assert response.status_code == 200
        r1.refresh_from_db()
        r2.refresh_from_db()
        assert r2.priority_order == 0
        assert r1.priority_order == 1

    def test_non_admin_cannot_save_rules(self, member_client, db):
        response = member_client.post(
            reverse("emails:settings_rules_save"),
            {"action": "add", "category": "Sales Lead", "assignee_id": 1},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Category visibility
# ---------------------------------------------------------------------------


class TestVisibilitySave:
    def test_save_replaces_all_visibility(self, admin_client, second_member, db):
        # Create existing visibility
        CategoryVisibility.objects.create(user=second_member, category="Vendor")

        response = admin_client.post(
            reverse("emails:settings_visibility_save"),
            {
                "user_id": second_member.pk,
                "categories[]": ["Sales Lead", "Complaint"],
            },
        )
        assert response.status_code == 200
        cats = set(
            CategoryVisibility.objects.filter(user=second_member).values_list("category", flat=True)
        )
        assert cats == {"Sales Lead", "Complaint"}
        # Old one gone
        assert "Vendor" not in cats

    def test_non_admin_cannot_save_visibility(self, member_client, db):
        response = member_client.post(
            reverse("emails:settings_visibility_save"),
            {"user_id": 1, "categories[]": ["Sales Lead"]},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# SLA config
# ---------------------------------------------------------------------------


class TestSLAConfigView:
    def test_create_new_config(self, admin_client, db):
        response = admin_client.post(
            reverse("emails:settings_sla_save"),
            {
                "priority": "HIGH",
                "category": "Sales Lead",
                "ack_hours": "2.0",
                "respond_hours": "8.0",
            },
        )
        assert response.status_code == 200
        cfg = SLAConfig.objects.get(priority="HIGH", category="Sales Lead")
        assert cfg.ack_hours == 2.0
        assert cfg.respond_hours == 8.0

    def test_update_existing_config(self, admin_client, db):
        SLAConfig.objects.create(
            priority="HIGH", category="Sales Lead", ack_hours=1.0, respond_hours=24.0,
        )
        response = admin_client.post(
            reverse("emails:settings_sla_save"),
            {
                "priority": "HIGH",
                "category": "Sales Lead",
                "ack_hours": "0.5",
                "respond_hours": "4.0",
            },
        )
        assert response.status_code == 200
        cfg = SLAConfig.objects.get(priority="HIGH", category="Sales Lead")
        assert cfg.ack_hours == 0.5
        assert cfg.respond_hours == 4.0

    def test_non_admin_cannot_save_sla(self, member_client, db):
        response = member_client.post(
            reverse("emails:settings_sla_save"),
            {"priority": "HIGH", "category": "Sales Lead", "ack_hours": "1", "respond_hours": "24"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Claim endpoint
# ---------------------------------------------------------------------------


class TestClaimEndpoint:
    def test_claim_succeeds(self, member_client, member_user, db):
        email = create_email()
        CategoryVisibility.objects.create(user=member_user, category="General Inquiry")
        response = member_client.post(reverse("emails:claim_email", args=[email.pk]))
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.assigned_to == member_user

    def test_claim_on_assigned_email_fails(self, member_client, member_user, admin_user, db):
        email = create_email(assigned_to=admin_user)
        CategoryVisibility.objects.create(user=member_user, category="General Inquiry")
        response = member_client.post(reverse("emails:claim_email", args=[email.pk]))
        assert response.status_code == 403

    def test_claim_without_visibility_fails(self, member_client, member_user, db):
        email = create_email()
        # No CategoryVisibility for member_user
        response = member_client.post(reverse("emails:claim_email", args=[email.pk]))
        assert response.status_code == 403

    def test_admin_can_claim_any_category(self, admin_client, admin_user, db):
        email = create_email(category="Complaint")
        response = admin_client.post(reverse("emails:claim_email", args=[email.pk]))
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.assigned_to == admin_user


# ---------------------------------------------------------------------------
# Thread claim endpoint
# ---------------------------------------------------------------------------


class TestThreadClaimEndpoint:
    def test_claim_thread_shows_toast(self, member_client, member_user, db):
        """POST to claim thread returns 'Thread claimed' toast."""
        thread = create_thread()
        CategoryVisibility.objects.create(user=member_user, category=thread.category)
        response = member_client.post(reverse("emails:claim_thread", args=[thread.pk]))
        assert response.status_code == 200
        assert b"Thread claimed" in response.content

    def test_admin_claim_thread_shows_toast(self, admin_client, admin_user, db):
        """Admin claiming thread also gets toast."""
        thread = create_thread()
        response = admin_client.post(reverse("emails:claim_thread", args=[thread.pk]))
        assert response.status_code == 200
        assert b"Thread claimed" in response.content


# ---------------------------------------------------------------------------
# AI suggestion endpoints
# ---------------------------------------------------------------------------


class TestAISuggestionEndpoints:
    def test_accept_assigns_email(self, admin_client, admin_user, second_member, db):
        email = create_email(ai_suggested_assignee={
            "name": second_member.get_full_name() or second_member.username,
            "user_id": second_member.pk,
            "reason": "Workload balanced",
        })
        response = admin_client.post(reverse("emails:accept_ai_suggestion", args=[email.pk]))
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.assigned_to == second_member

    def test_reject_clears_suggestion(self, admin_client, admin_user, db):
        email = create_email(ai_suggested_assignee={
            "name": "Someone",
            "user_id": 999,
            "reason": "test",
        })
        response = admin_client.post(reverse("emails:reject_ai_suggestion", args=[email.pk]))
        assert response.status_code == 200
        email.refresh_from_db()
        assert email.ai_suggested_assignee == {}

    def test_non_admin_cannot_accept(self, member_client, db):
        email = create_email()
        response = member_client.post(reverse("emails:accept_ai_suggestion", args=[email.pk]))
        assert response.status_code == 403

    def test_non_admin_cannot_reject(self, member_client, db):
        email = create_email()
        response = member_client.post(reverse("emails:reject_ai_suggestion", args=[email.pk]))
        assert response.status_code == 403

    def test_accept_with_no_suggestion_fails(self, admin_client, admin_user, db):
        email = create_email(ai_suggested_assignee={})
        response = admin_client.post(reverse("emails:accept_ai_suggestion", args=[email.pk]))
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# SLA template filters
# ---------------------------------------------------------------------------


class TestSLAFilters:
    def test_sla_color_none(self):
        from apps.emails.templatetags.email_tags import sla_color
        assert sla_color(None) == "slate"

    def test_sla_color_breached(self):
        from apps.emails.templatetags.email_tags import sla_color
        past = dj_timezone.now() - timedelta(hours=1)
        assert sla_color(past) == "red animate-pulse"

    def test_sla_color_emerald(self):
        from apps.emails.templatetags.email_tags import sla_color
        future = dj_timezone.now() + timedelta(hours=3)
        assert sla_color(future) == "emerald"

    def test_sla_color_amber(self):
        from apps.emails.templatetags.email_tags import sla_color
        future = dj_timezone.now() + timedelta(hours=1, minutes=30)
        assert sla_color(future) == "amber"

    def test_sla_color_orange(self):
        from apps.emails.templatetags.email_tags import sla_color
        future = dj_timezone.now() + timedelta(minutes=45)
        assert sla_color(future) == "orange"

    def test_sla_color_red(self):
        from apps.emails.templatetags.email_tags import sla_color
        future = dj_timezone.now() + timedelta(minutes=15)
        assert sla_color(future) == "red"

    def test_sla_countdown_none(self):
        from apps.emails.templatetags.email_tags import sla_countdown
        assert sla_countdown(None) == "--"

    def test_sla_countdown_breached(self):
        from apps.emails.templatetags.email_tags import sla_countdown
        past = dj_timezone.now() - timedelta(hours=2, minutes=15)
        result = sla_countdown(past)
        assert result.startswith("-")
        assert "2h" in result

    def test_sla_countdown_remaining(self):
        from apps.emails.templatetags.email_tags import sla_countdown
        future = dj_timezone.now() + timedelta(hours=3, minutes=30)
        result = sla_countdown(future)
        assert "3h" in result

    def test_sla_countdown_under_hour(self):
        from apps.emails.templatetags.email_tags import sla_countdown
        future = dj_timezone.now() + timedelta(minutes=45)
        result = sla_countdown(future)
        assert "h" not in result
        assert "m" in result


# ---------------------------------------------------------------------------
# Inboxes tab
# ---------------------------------------------------------------------------


class TestInboxesTab:
    def test_inboxes_tab_renders(self, admin_client, db):
        SystemConfig.objects.update_or_create(
            key="monitored_inboxes",
            defaults={"value": "info@vidarbhainfotech.com", "value_type": "str", "category": "email"},
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=inboxes")
        assert response.status_code == 200
        assert "info@vidarbhainfotech.com" in response.content.decode()

    def test_inboxes_add(self, admin_client, db):
        SystemConfig.objects.update_or_create(
            key="monitored_inboxes",
            defaults={"value": "", "value_type": "str", "category": "email"},
        )
        response = admin_client.post(
            reverse("emails:settings_inboxes_save"),
            {"action": "add", "inbox_email": "test@example.com"},
        )
        assert response.status_code == 200
        cfg = SystemConfig.objects.get(key="monitored_inboxes")
        assert "test@example.com" in cfg.value

    def test_inboxes_add_duplicate(self, admin_client, db):
        SystemConfig.objects.update_or_create(
            key="monitored_inboxes",
            defaults={"value": "test@example.com", "value_type": "str", "category": "email"},
        )
        response = admin_client.post(
            reverse("emails:settings_inboxes_save"),
            {"action": "add", "inbox_email": "test@example.com"},
        )
        assert response.status_code == 200
        cfg = SystemConfig.objects.get(key="monitored_inboxes")
        # Should not have duplicates
        parts = [p.strip() for p in cfg.value.split(",") if p.strip()]
        assert parts.count("test@example.com") == 1

    def test_inboxes_remove(self, admin_client, db):
        SystemConfig.objects.update_or_create(
            key="monitored_inboxes",
            defaults={"value": "info@vidarbhainfotech.com,test@example.com", "value_type": "str", "category": "email"},
        )
        response = admin_client.post(
            reverse("emails:settings_inboxes_save"),
            {"action": "remove", "inbox_email": "test@example.com"},
        )
        assert response.status_code == 200
        cfg = SystemConfig.objects.get(key="monitored_inboxes")
        assert "test@example.com" not in cfg.value
        assert "info@vidarbhainfotech.com" in cfg.value

    def test_inboxes_admin_required(self, member_client, db):
        response = member_client.post(
            reverse("emails:settings_inboxes_save"),
            {"action": "add", "inbox_email": "test@example.com"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Config editor tab
# ---------------------------------------------------------------------------


class TestConfigEditor:
    def test_config_tab_renders(self, admin_client, db):
        SystemConfig.objects.create(
            key="test_key", value="test_val", value_type="str",
            category="testing", description="A test config",
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=config")
        assert response.status_code == 200
        content = response.content.decode()
        assert "test_key" in content
        assert "testing" in content

    def test_config_save(self, admin_client, db):
        SystemConfig.objects.create(
            key="my_setting", value="old", value_type="str", category="demo",
        )
        response = admin_client.post(
            reverse("emails:settings_config_save"),
            {"category": "demo", "config_my_setting": "new_value"},
        )
        assert response.status_code == 200
        cfg = SystemConfig.objects.get(key="my_setting")
        assert cfg.value == "new_value"

    def test_config_save_preserves_type(self, admin_client, db):
        SystemConfig.objects.create(
            key="flag_enabled", value="true", value_type="bool", category="flags",
        )
        # Submit with checkbox unchecked (no field sent)
        response = admin_client.post(
            reverse("emails:settings_config_save"),
            {"category": "flags"},
        )
        assert response.status_code == 200
        cfg = SystemConfig.objects.get(key="flag_enabled")
        assert cfg.value_type == "bool"  # type preserved
        assert cfg.value == "false"  # unchecked = false

    def test_config_editor_admin_required(self, member_client, db):
        response = member_client.post(
            reverse("emails:settings_config_save"),
            {"category": "demo", "config_something": "val"},
        )
        assert response.status_code == 403

    def test_config_string_prefilled(self, admin_client, db):
        """R2.2: String input renders with value= matching DB value."""
        SystemConfig.objects.create(
            key="test_str_prefill", value="hello_world", value_type="str",
            category="r22test",
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=config")
        content = response.content.decode()
        assert 'value="hello_world"' in content

    def test_config_bool_checked_when_true(self, admin_client, db):
        """R2.2: Bool checkbox renders as checked when value='true'."""
        SystemConfig.objects.create(
            key="test_bool_prefill", value="true", value_type="bool",
            category="r22test",
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=config")
        content = response.content.decode()
        assert "test_bool_prefill" in content
        # The checkbox should have 'checked' attribute
        assert "checked" in content

    def test_config_int_prefilled(self, admin_client, db):
        """R2.2: Int input renders with value= matching DB value."""
        SystemConfig.objects.create(
            key="test_int_prefill", value="42", value_type="int",
            category="r22test",
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=config")
        content = response.content.decode()
        assert 'value="42"' in content

    def test_config_bool_has_hidden_fallback(self, admin_client, db):
        """Config editor checkbox has hidden input fallback for unchecked state."""
        SystemConfig.objects.create(
            key="test_hidden", value="false", value_type="bool",
            category="r22test",
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=config")
        content = response.content.decode()
        # Hidden input with value="false" should appear before checkbox
        assert 'type="hidden"' in content
        assert 'value="false"' in content

    def test_config_json_renders_textarea(self, admin_client, db):
        """Config editor JSON type renders as textarea."""
        SystemConfig.objects.create(
            key="test_json_ta", value='{"key": "val"}', value_type="json",
            category="r22test",
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=config")
        content = response.content.decode()
        assert "<textarea" in content
        # Template auto-escapes quotes in HTML
        assert "test_json_ta" in content
        assert "&quot;key&quot;" in content or '{"key"' in content


# ---------------------------------------------------------------------------
# Whitelist CRUD views
# ---------------------------------------------------------------------------


class TestWhitelistViews:
    def test_whitelist_add_creates_entry(self, admin_client, admin_user, db):
        response = admin_client.post(
            reverse("emails:whitelist_add"),
            {"entry": "john@acme.com", "entry_type": "email"},
        )
        assert response.status_code == 200
        assert SpamWhitelist.objects.filter(entry="john@acme.com", entry_type="email").exists()

    def test_whitelist_add_rejects_non_admin(self, member_client, db):
        response = member_client.post(
            reverse("emails:whitelist_add"),
            {"entry": "john@acme.com", "entry_type": "email"},
        )
        assert response.status_code == 403

    def test_whitelist_add_rejects_empty_entry(self, admin_client, admin_user, db):
        response = admin_client.post(
            reverse("emails:whitelist_add"),
            {"entry": "", "entry_type": "email"},
        )
        assert response.status_code == 200
        assert SpamWhitelist.objects.count() == 0
        content = response.content.decode()
        assert "cannot be empty" in content.lower() or "error" in content.lower()

    def test_whitelist_add_handles_duplicate(self, admin_client, admin_user, db):
        SpamWhitelist.objects.create(
            entry="john@acme.com", entry_type="email", added_by=admin_user,
        )
        response = admin_client.post(
            reverse("emails:whitelist_add"),
            {"entry": "john@acme.com", "entry_type": "email"},
        )
        assert response.status_code == 200
        # Should not crash, should show already-exists message
        assert SpamWhitelist.objects.filter(entry="john@acme.com").count() == 1

    def test_whitelist_delete_soft_deletes(self, admin_client, admin_user, db):
        wl = SpamWhitelist.objects.create(
            entry="john@acme.com", entry_type="email", added_by=admin_user,
        )
        response = admin_client.post(
            reverse("emails:whitelist_delete", args=[wl.pk]),
        )
        assert response.status_code == 200
        # Soft-deleted: still exists in DB but not in default queryset
        assert not SpamWhitelist.objects.filter(pk=wl.pk).exists()

    def test_settings_view_includes_whitelist_entries(self, admin_client, admin_user, db):
        SpamWhitelist.objects.create(
            entry="test@example.com", entry_type="email", added_by=admin_user,
        )
        response = admin_client.get(reverse("emails:settings") + "?tab=whitelist")
        assert response.status_code == 200
        content = response.content.decode()
        assert "test@example.com" in content


class TestWhitelistSender:
    def test_whitelist_sender_creates_entry(self, admin_client, admin_user, db):
        email = create_email(from_address="spammer@example.com")
        response = admin_client.post(
            reverse("emails:whitelist_sender", args=[email.pk]),
        )
        assert response.status_code == 200
        assert SpamWhitelist.objects.filter(entry="spammer@example.com", entry_type="email").exists()

    def test_whitelist_sender_unspams_existing_emails(self, admin_client, admin_user, db):
        email = create_email(from_address="spammer@example.com", is_spam=True)
        admin_client.post(reverse("emails:whitelist_sender", args=[email.pk]))
        email.refresh_from_db()
        assert email.is_spam is False

    def test_whitelist_sender_returns_detail_panel(self, admin_client, admin_user, db):
        email = create_email(from_address="spammer@example.com")
        response = admin_client.post(
            reverse("emails:whitelist_sender", args=[email.pk]),
        )
        content = response.content.decode()
        # Returns refreshed detail panel with email subject
        assert email.subject in content

    def test_whitelist_sender_rejects_non_admin(self, member_client, member_user, db):
        email = create_email()
        response = member_client.post(
            reverse("emails:whitelist_sender", args=[email.pk]),
        )
        assert response.status_code == 403

    def test_whitelist_sender_handles_already_whitelisted(self, admin_client, admin_user, db):
        email = create_email(from_address="known@example.com")
        SpamWhitelist.objects.create(
            entry="known@example.com", entry_type="email", added_by=admin_user,
        )
        response = admin_client.post(
            reverse("emails:whitelist_sender", args=[email.pk]),
        )
        assert response.status_code == 200


class TestSaveFeedbackBanners:
    def test_sla_save_returns_save_success(self, admin_client, db):
        response = admin_client.post(
            reverse("emails:settings_sla_save"),
            {"priority": "HIGH", "category": "Sales Lead", "ack_hours": "2.0", "respond_hours": "8.0"},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "saved" in content.lower()

    def test_rules_save_returns_save_success(self, admin_client, admin_user, second_member, db):
        response = admin_client.post(
            reverse("emails:settings_rules_save"),
            {"action": "add", "category": "Sales Lead", "assignee_id": second_member.pk},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "saved" in content.lower()

    def test_visibility_save_returns_save_success(self, admin_client, second_member, db):
        response = admin_client.post(
            reverse("emails:settings_visibility_save"),
            {"user_id": second_member.pk, "categories[]": ["Sales Lead"]},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "saved" in content.lower()

    def test_inboxes_save_returns_save_success(self, admin_client, db):
        SystemConfig.objects.update_or_create(
            key="monitored_inboxes",
            defaults={"value": "", "value_type": "str", "category": "email"},
        )
        response = admin_client.post(
            reverse("emails:settings_inboxes_save"),
            {"action": "add", "inbox_email": "new@example.com"},
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "saved" in content.lower()
