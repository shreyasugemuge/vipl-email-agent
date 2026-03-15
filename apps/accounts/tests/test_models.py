"""Tests for the custom User model."""

import pytest

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserModel:
    def test_role_defaults_to_member(self):
        user = User.objects.create_user(username="testuser", password="pass123")
        assert user.role == User.Role.MEMBER

    def test_can_see_all_emails_defaults_to_false(self):
        user = User.objects.create_user(username="testuser", password="pass123")
        assert user.can_see_all_emails is False

    def test_is_admin_role_true_for_admin(self):
        user = User.objects.create_user(
            username="admin", password="pass123", role=User.Role.ADMIN
        )
        assert user.is_admin_role is True

    def test_is_admin_role_false_for_member(self):
        user = User.objects.create_user(
            username="member", password="pass123", role=User.Role.MEMBER
        )
        assert user.is_admin_role is False

    def test_role_choices(self):
        assert User.Role.ADMIN == "admin"
        assert User.Role.TRIAGE_LEAD == "triage_lead"
        assert User.Role.MEMBER == "member"


@pytest.mark.django_db
class TestPermissionProperties:
    """Test all 5 permission properties across 3 roles."""

    def test_admin_can_assign(self, admin_user):
        assert admin_user.can_assign is True

    def test_triage_lead_can_assign(self, triage_lead_user):
        assert triage_lead_user.can_assign is True

    def test_member_cannot_assign(self, member_user):
        assert member_user.can_assign is False

    def test_admin_is_admin_only(self, admin_user):
        assert admin_user.is_admin_only is True

    def test_triage_lead_not_admin_only(self, triage_lead_user):
        assert triage_lead_user.is_admin_only is False

    def test_member_not_admin_only(self, member_user):
        assert member_user.is_admin_only is False

    def test_admin_can_triage(self, admin_user):
        assert admin_user.can_triage is True

    def test_triage_lead_can_triage(self, triage_lead_user):
        assert triage_lead_user.can_triage is True

    def test_member_cannot_triage(self, member_user):
        assert member_user.can_triage is False

    def test_admin_can_approve_users(self, admin_user):
        assert admin_user.can_approve_users is True

    def test_triage_lead_can_approve_users(self, triage_lead_user):
        assert triage_lead_user.can_approve_users is True

    def test_member_cannot_approve_users(self, member_user):
        assert member_user.can_approve_users is False

    def test_triage_lead_is_triage_lead(self, triage_lead_user):
        assert triage_lead_user.is_triage_lead is True

    def test_admin_not_triage_lead(self, admin_user):
        assert admin_user.is_triage_lead is False

    def test_is_staff_false_for_triage_lead(self, triage_lead_user):
        assert triage_lead_user.is_staff is False
