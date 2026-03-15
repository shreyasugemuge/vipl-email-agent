"""Tests for Google OAuth SSO via django-allauth."""

import logging

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

    def test_auto_link_saves_avatar_on_existing_user(self):
        """When auto-linking an existing user (not yet linked), avatar should
        be saved using existing_user directly, not sociallogin.user."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        user = User.objects.create_user(
            username="unlinked",
            email="unlinked@vidarbhainfotech.com",
            avatar_url="",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="unlinked@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="https://google.com/avatar/new.jpg",
            is_existing=False,
        )
        # Simulate connect() — sociallogin.user might NOT be set to existing_user
        sociallogin.connect = MagicMock()

        adapter.pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert user.avatar_url == "https://google.com/avatar/new.jpg"
        sociallogin.connect.assert_called_once_with(request, user)

    def test_auto_link_no_avatar_when_picture_empty(self):
        """If Google returns no picture, avatar_url should stay empty."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        user = User.objects.create_user(
            username="nopic",
            email="nopic@vidarbhainfotech.com",
            avatar_url="",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="nopic@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="",
            is_existing=False,
        )
        sociallogin.connect = MagicMock()

        adapter.pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert user.avatar_url == ""

    def test_repeat_login_skips_save_when_avatar_unchanged(self):
        """Repeat login with same avatar should not trigger a DB save."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        avatar = "https://google.com/avatar/same.jpg"
        user = User.objects.create_user(
            username="repeat",
            email="repeat@vidarbhainfotech.com",
            avatar_url=avatar,
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="repeat@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture=avatar,
            is_existing=True,
            user=user,
        )

        with patch.object(User, "save") as mock_save:
            adapter.pre_social_login(request, sociallogin)
            mock_save.assert_not_called()

    def test_auto_link_welcome_message_uses_first_name(self):
        """Welcome message should use first_name when available."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        user = User.objects.create_user(
            username="shreyas",
            email="shreyas@vidarbhainfotech.com",
            first_name="Shreyas",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="shreyas@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            is_existing=False,
        )
        sociallogin.connect = MagicMock()

        adapter.pre_social_login(request, sociallogin)

        msgs = [m.message for m in get_messages(request)]
        assert any("Shreyas" in m for m in msgs)

    def test_auto_link_welcome_message_falls_back_to_username(self):
        """Welcome message should use username when first_name is empty."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        user = User.objects.create_user(
            username="dev1",
            email="dev1@vidarbhainfotech.com",
            first_name="",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="dev1@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            is_existing=False,
        )
        sociallogin.connect = MagicMock()

        adapter.pre_social_login(request, sociallogin)

        msgs = [m.message for m in get_messages(request)]
        assert any("dev1" in m for m in msgs)

    def test_new_user_not_in_db_returns_early(self):
        """Brand new email (no User row) should return without error,
        letting allauth proceed to save_user()."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="brandnew@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            is_existing=False,
        )

        # Should not raise
        result = adapter.pre_social_login(request, sociallogin)
        assert result is None

    def test_connect_exception_propagates(self):
        """If connect() raises an unexpected error, it should propagate."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        User.objects.create_user(
            username="erroruser",
            email="error@vidarbhainfotech.com",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="error@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            is_existing=False,
        )
        sociallogin.connect = MagicMock(side_effect=RuntimeError("DB down"))

        with pytest.raises(RuntimeError, match="DB down"):
            adapter.pre_social_login(request, sociallogin)

    def test_domain_rejection_logs_warning(self, caplog):
        """Rejected logins should produce a warning log."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="hacker@evil.com", hd="evil.com"
        )

        with caplog.at_level(logging.WARNING, logger="apps.accounts.adapters"):
            with pytest.raises(ImmediateHttpResponse):
                adapter.pre_social_login(request, sociallogin)

        assert "OAuth rejected" in caplog.text
        assert "hacker@evil.com" in caplog.text

    def test_domain_rejection_sets_error_message(self):
        """Rejected login should set a user-visible error message."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="user@othercorp.com", hd="othercorp.com"
        )

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)

        msgs = [m.message for m in get_messages(request)]
        assert any("vidarbhainfotech.com" in m for m in msgs)

    def test_empty_email_rejected(self):
        """Empty email in extra_data should be rejected."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(email="", hd="")

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)

    def test_email_suffix_attack_rejected(self):
        """Email like 'evil@attacker.com@vidarbhainfotech.com' with wrong hd
        should be rejected."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="evil@attacker.com@vidarbhainfotech.com",
            hd="attacker.com",
        )

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, sociallogin)


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


@pytest.mark.django_db
class TestSuperadminAutoApproval:
    """Tests for superadmin auto-approval in save_user."""

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": "boss@vidarbhainfotech.com"})
    def test_superadmin_gets_full_access(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="boss",
            email="boss@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="boss@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="https://avatar.example.com/boss.jpg",
        )
        sociallogin.user = user

        result = adapter.save_user(request, sociallogin, form=None)

        result.refresh_from_db()
        assert result.is_active is True
        assert result.role == "admin"
        assert result.is_staff is True
        assert result.is_superuser is True
        assert result.can_see_all_emails is True
        assert result.avatar_url == "https://avatar.example.com/boss.jpg"

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": "Boss@Vidarbhainfotech.com"})
    def test_superadmin_email_case_insensitive(self):
        """SUPERADMIN_EMAILS comparison should be case-insensitive."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="boss2",
            email="boss@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="boss@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
        )
        sociallogin.user = user

        result = adapter.save_user(request, sociallogin, form=None)

        result.refresh_from_db()
        assert result.is_active is True
        assert result.role == "admin"

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": ""})
    def test_no_superadmin_env_makes_everyone_pending(self):
        """With empty SUPERADMIN_EMAILS, all users are pending."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="anyone",
            email="anyone@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="anyone@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
        )
        sociallogin.user = user

        with pytest.raises(ImmediateHttpResponse):
            adapter.save_user(request, sociallogin, form=None)

        user.refresh_from_db()
        assert user.is_active is False

    @patch("apps.accounts.adapters.send_mail", side_effect=Exception("SMTP down"))
    def test_admin_notification_failure_does_not_block_signup(self, mock_send, settings):
        """If admin email fails, signup should still proceed."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        settings.ADMIN_EMAIL = "admin@vidarbhainfotech.com"
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="newbie",
            email="newbie@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="newbie@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
        )
        sociallogin.user = user

        with pytest.raises(ImmediateHttpResponse):
            adapter.save_user(request, sociallogin, form=None)

        user.refresh_from_db()
        assert user.is_active is False
        assert user.role == "member"

    def test_new_user_without_avatar_gets_empty_string(self):
        """New user with no Google picture should have empty avatar_url."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter
        from allauth.core.exceptions import ImmediateHttpResponse

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        user = User.objects.create_user(
            username="noavatar",
            email="noavatar@vidarbhainfotech.com",
        )
        sociallogin = _make_sociallogin(
            email="noavatar@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="",
        )
        sociallogin.user = user

        with pytest.raises(ImmediateHttpResponse):
            adapter.save_user(request, sociallogin, form=None)

        user.refresh_from_db()
        assert user.avatar_url == ""


@pytest.mark.django_db
class TestAuthenticationError:
    """Tests for authentication_error handler."""

    def test_logs_error_details(self, caplog):
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        with caplog.at_level(logging.ERROR, logger="apps.accounts.adapters"):
            result = adapter.authentication_error(
                request,
                provider_id="google",
                error="access_denied",
                exception=ValueError("token expired"),
            )

        assert "OAuth error" in caplog.text
        assert "google" in caplog.text
        assert "access_denied" in caplog.text
        assert result.status_code == 302
        assert "error=auth" in result.url

    def test_sets_user_visible_error_message(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        adapter.authentication_error(
            request,
            provider_id="google",
            error="server_error",
        )

        msgs = [m.message for m in get_messages(request)]
        assert any("failed" in m.lower() for m in msgs)

    def test_handles_none_error_gracefully(self):
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        adapter = VIPLSocialAccountAdapter()
        request = _make_request()

        result = adapter.authentication_error(
            request,
            provider_id="google",
            error=None,
            exception=None,
        )

        assert result.status_code == 302


@pytest.mark.django_db
class TestGetSuperadminEmails:
    """Tests for _get_superadmin_emails helper."""

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": "a@b.com, C@D.COM ,  e@f.com  "})
    def test_parses_comma_separated_and_lowercases(self):
        from apps.accounts.adapters import _get_superadmin_emails

        result = _get_superadmin_emails()
        assert result == {"a@b.com", "c@d.com", "e@f.com"}

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": ""})
    def test_empty_string_returns_empty_set(self):
        from apps.accounts.adapters import _get_superadmin_emails

        assert _get_superadmin_emails() == set()

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_env_var_returns_empty_set(self):
        from apps.accounts.adapters import _get_superadmin_emails

        assert _get_superadmin_emails() == set()

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": "only@one.com"})
    def test_single_email_works(self):
        from apps.accounts.adapters import _get_superadmin_emails

        assert _get_superadmin_emails() == {"only@one.com"}

    @patch.dict("os.environ", {"SUPERADMIN_EMAILS": ",,, ,,"})
    def test_only_commas_returns_empty_set(self):
        from apps.accounts.adapters import _get_superadmin_emails

        assert _get_superadmin_emails() == set()


@pytest.mark.django_db
class TestAvatarEdgeCases:
    """Edge case tests for avatar import (FIX-01 verification).

    Avatar import works correctly. If avatars disappear after time,
    it's Google URL expiry (signed URL TTL), not a Django bug.
    """

    def test_avatar_url_with_query_params(self):
        """Signed Google avatar URL with query params is stored correctly."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        signed_url = "https://lh3.googleusercontent.com/a/ACg8ocK...=s96-c"
        user = User.objects.create_user(
            username="signedurl",
            email="signedurl@vidarbhainfotech.com",
            avatar_url="",
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="signedurl@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture=signed_url,
            is_existing=True,
            user=user,
        )

        adapter.pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert user.avatar_url == signed_url

    def test_avatar_url_empty_string_does_not_overwrite_existing(self):
        """Empty string picture from Google does not overwrite existing avatar."""
        from apps.accounts.adapters import VIPLSocialAccountAdapter

        existing_avatar = "https://lh3.googleusercontent.com/a/existing.jpg"
        user = User.objects.create_user(
            username="keepavatar",
            email="keepavatar@vidarbhainfotech.com",
            avatar_url=existing_avatar,
        )
        adapter = VIPLSocialAccountAdapter()
        request = _make_request()
        sociallogin = _make_sociallogin(
            email="keepavatar@vidarbhainfotech.com",
            hd="vidarbhainfotech.com",
            picture="",  # Google returns empty
            is_existing=True,
            user=user,
        )

        adapter.pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert user.avatar_url == existing_avatar
