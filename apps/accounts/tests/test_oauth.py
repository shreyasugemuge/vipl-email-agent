"""Tests for Google OAuth SSO via django-allauth."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from django.test import Client, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage

from apps.accounts.models import User


def _make_request(path="/"):
    """Create a request with session and messages middleware applied."""
    factory = RequestFactory()
    request = factory.get(path)
    # Add session
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    # Add messages
    setattr(request, "_messages", FallbackStorage(request))
    return request


def _make_sociallogin(email, hd=None, picture="", is_existing=False, user=None):
    """Create a mock sociallogin object mimicking allauth's SocialLogin."""
    extra_data = {"email": email, "picture": picture}
    if hd is not None:
        extra_data["hd"] = hd

    account = MagicMock()
    account.extra_data = extra_data

    sociallogin = MagicMock()
    sociallogin.account = account
    sociallogin.is_existing = is_existing
    if user:
        sociallogin.user = user
    else:
        sociallogin.user = MagicMock()

    return sociallogin


@pytest.mark.django_db
class TestVIPLSocialAccountAdapterPreSocialLogin:
    """Tests for domain enforcement in pre_social_login."""

    def test_rejects_gmail_domain(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="user@gmail.com", hd="gmail.com"
        )

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)

    def test_allows_vipl_domain(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="shreyas@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
        )

        # Should not raise
        adapter.pre_social_login(request, sociallogin)

    def test_rejects_spoofed_email_wrong_hd(self):
        """Even if email looks correct, reject if hd claim doesn't match."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="user@vidarbhainfotech.com",
            hd="otherdomain.com",
        )

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)

    def test_rejects_missing_hd_claim(self):
        """Personal Google accounts have no hd claim - must reject."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="user@vidarbhainfotech.com",
            hd=None,  # no hd in extra_data
        )

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)

    def test_updates_avatar_on_existing_user_login(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        user = User.objects.create_user(
            username="shreyas",
            email="shreyas@vidarbhainfotech.com",
            avatar_url="https://old-avatar.example.com/photo.jpg",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="shreyas@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="https://new-avatar.example.com/photo.jpg",
            is_existing=True,
            user=user,
        )

        adapter.pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert user.avatar_url == "https://new-avatar.example.com/photo.jpg"


@pytest.mark.django_db
class TestVIPLSocialAccountAdapterSaveUser:
    """Tests for new user creation in save_user."""

    def test_new_user_created_inactive(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="newuser",
            email="newuser@vidarbhainfotech.com",
            is_active=True,
        )
        sociallogin = _make_sociallogin(
            email="newuser@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="https://avatar.example.com/photo.jpg",
        )
        sociallogin.user = user

        with patch.object(
            type(adapter), "save_user",
            wraps=adapter.save_user,
        ):
            # save_user raises ImmediateHttpResponse after setting user inactive
            with pytest.raises(ImmediateHttpResponse):
                adapter.save_user(request, sociallogin, form=None)

        user.refresh_from_db()
        assert user.is_active is False
        assert user.role == "member"
        assert user.can_see_all_emails is False

    def test_stores_avatar_url_on_new_user(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="newuser2",
            email="new2@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="new2@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="https://avatar.example.com/pic.jpg",
        )
        sociallogin.user = user

        with pytest.raises(ImmediateHttpResponse):
            adapter.save_user(request, sociallogin, form=None)

        user.refresh_from_db()
        assert user.avatar_url == "https://avatar.example.com/pic.jpg"

    @patch("apps.accounts.adapters.send_mail")
    def test_admin_notified_on_new_user(self, mock_send_mail, settings):
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        settings.ADMIN_EMAIL = "admin@vidarbhainfotech.com"
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="newuser3",
            email="new3@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="new3@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
        )
        sociallogin.user = user

        with pytest.raises(ImmediateHttpResponse):
            adapter.save_user(request, sociallogin, form=None)

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args
        assert "new3@vidarbhainfotech.com" in call_kwargs[1].get("subject", "") or "new3@vidarbhainfotech.com" in str(call_kwargs)


@pytest.mark.django_db
class TestPasswordLoginPreserved:
    """Ensure password login at ?password=1 still works."""

    def test_password_login_works_at_password_param(self, client):
        User.objects.create_user(username="admin", password="adminpass123")
        response = client.post(
            "/accounts/login/?password=1",
            {"username": "admin", "password": "adminpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/emails/"

    def test_login_page_renders_without_error(self, client):
        response = client.get("/accounts/login/")
        assert response.status_code == 200

    def test_login_page_with_password_param_renders(self, client):
        response = client.get("/accounts/login/?password=1")
        assert response.status_code == 200


@pytest.mark.django_db
class TestDataMigration:
    """Test the superuser email data migration logic."""

    def test_superuser_with_blank_email_gets_email_set(self):
        """Superusers with blank email should get email set to username@vidarbhainfotech.com."""
        user = User.objects.create_superuser(
            username="shreyas", password="pass123", email=""
        )
        assert user.email == ""

        # Simulate migration logic
        from apps.accounts.migration_helpers import set_superuser_emails
        set_superuser_emails(User)

        user.refresh_from_db()
        assert user.email == "shreyas@vidarbhainfotech.com"

    def test_superuser_with_existing_email_unchanged(self):
        """Superusers with existing email should not be modified."""
        user = User.objects.create_superuser(
            username="admin", password="pass123", email="custom@example.com"
        )

        from apps.accounts.migration_helpers import set_superuser_emails
        set_superuser_emails(User)

        user.refresh_from_db()
        assert user.email == "custom@example.com"

    def test_non_superuser_unchanged(self):
        """Normal users should not be affected by the migration."""
        user = User.objects.create_user(
            username="member", password="pass123", email=""
        )

        from apps.accounts.migration_helpers import set_superuser_emails
        set_superuser_emails(User)

        user.refresh_from_db()
        assert user.email == ""
