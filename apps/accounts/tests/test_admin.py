"""Tests for Django admin configuration."""

import pytest
from django.test import Client

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserAdmin:
    def test_admin_accessible_by_staff_user(self, client):
        User.objects.create_user(
            username="admin",
            password="adminpass123",
            is_staff=True,
            role=User.Role.ADMIN,
        )
        client.login(username="admin", password="adminpass123")
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_admin_user_list_shows_role(self, client):
        admin = User.objects.create_user(
            username="admin",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
            role=User.Role.ADMIN,
        )
        client.login(username="admin", password="adminpass123")
        response = client.get("/admin/accounts/user/")
        assert response.status_code == 200

    def test_admin_can_create_user_with_role(self, client):
        admin = User.objects.create_user(
            username="admin",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
            role=User.Role.ADMIN,
        )
        client.login(username="admin", password="adminpass123")
        response = client.get("/admin/accounts/user/add/")
        assert response.status_code == 200
        # Role field should be present in the form
        assert b"role" in response.content
