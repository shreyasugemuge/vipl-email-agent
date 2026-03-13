"""Tests for authentication views."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.django_db
class TestLogin:
    def test_login_page_renders(self, client):
        response = client.get("/accounts/login/")
        assert response.status_code == 200

    def test_login_with_valid_credentials(self, client):
        User.objects.create_user(username="testuser", password="testpass123")
        response = client.post(
            "/accounts/login/",
            {"username": "testuser", "password": "testpass123"},
        )
        # Successful login redirects
        assert response.status_code == 302
        assert response.url == "/emails/"

    def test_login_with_invalid_credentials(self, client):
        User.objects.create_user(username="testuser", password="testpass123")
        response = client.post(
            "/accounts/login/",
            {"username": "testuser", "password": "wrongpassword"},
        )
        # Failed login stays on login page (200, not redirect)
        assert response.status_code == 200


@pytest.mark.django_db
class TestLogout:
    def test_logout_redirects_to_login(self, client):
        user = User.objects.create_user(username="testuser", password="testpass123")
        client.login(username="testuser", password="testpass123")
        response = client.post("/accounts/logout/")
        assert response.status_code == 302
        assert "/accounts/login/" in response.url


@pytest.mark.django_db
class TestProtectedView:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/emails/")
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_authenticated_user_can_access_dashboard(self, client):
        User.objects.create_user(username="testuser", password="testpass123")
        client.login(username="testuser", password="testpass123")
        response = client.get("/emails/")
        assert response.status_code == 200

    def test_old_dashboard_redirects_to_emails(self, client):
        """Legacy /accounts/dashboard/ redirects to /emails/."""
        User.objects.create_user(username="testuser", password="testpass123")
        client.login(username="testuser", password="testpass123")
        response = client.get("/accounts/dashboard/")
        assert response.status_code == 302
        assert response.url == "/emails/"
