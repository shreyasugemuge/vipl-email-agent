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
        assert User.Role.MEMBER == "member"
