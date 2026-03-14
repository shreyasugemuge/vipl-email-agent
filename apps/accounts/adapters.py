"""Custom allauth adapter for VIPL Email Agent.

Enforces @vidarbhainfotech.com domain server-side and auto-creates
new Google users as inactive pending admin approval.
shreyas@vidarbhainfotech.com is auto-approved as superadmin.
"""

import logging
import os

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect

from .models import User

logger = logging.getLogger(__name__)
ALLOWED_DOMAIN = "vidarbhainfotech.com"
SUPERADMIN_EMAIL = "shreyas@vidarbhainfotech.com"


class VIPLSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Domain-locked Google OAuth adapter for VIPL."""

    def pre_social_login(self, request, sociallogin):
        """Enforce @vidarbhainfotech.com domain. Auto-link existing users."""
        extra_data = sociallogin.account.extra_data
        email = extra_data.get("email", "")
        hd = extra_data.get("hd", "")

        # SECURITY: Check both email suffix AND hd claim from Google ID token
        if not email.endswith(f"@{ALLOWED_DOMAIN}") or hd != ALLOWED_DOMAIN:
            logger.warning("OAuth rejected: email=%s hd=%s", email, hd)
            messages.error(
                request, "Only @vidarbhainfotech.com accounts can sign in."
            )
            raise ImmediateHttpResponse(redirect("/accounts/login/?error=domain"))

        # Auto-link: if a user with this email exists but isn't linked to a
        # social account, connect them now. This is safe because we've already
        # verified the domain via Google's hd claim (tamper-proof).
        if not sociallogin.is_existing:
            try:
                existing_user = User.objects.get(email=email)
                sociallogin.connect(request, existing_user)
                logger.info("Auto-linked Google account to existing user %s", email)
            except User.DoesNotExist:
                return  # New user — will go through save_user()

        # Update avatar for linked users
        user = sociallogin.user
        picture = extra_data.get("picture", "")
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            user.save(update_fields=["avatar_url"])
        first_name = user.first_name or user.username
        messages.info(request, f"Welcome, {first_name}!")

    def save_user(self, request, sociallogin, form=None):
        """Auto-create new Google users. Superadmin is auto-approved."""
        user = super().save_user(request, sociallogin, form)
        extra_data = sociallogin.account.extra_data
        email = user.email or extra_data.get("email", "")

        # Superadmin: auto-approve with full access
        if email == SUPERADMIN_EMAIL:
            user.is_active = True
            user.role = User.Role.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.can_see_all_emails = True
            user.avatar_url = extra_data.get("picture", "")
            user.save(
                update_fields=[
                    "is_active", "role", "is_staff", "is_superuser",
                    "can_see_all_emails", "avatar_url",
                ]
            )
            messages.success(request, f"Welcome, {user.first_name}!")
            return user

        # Everyone else: inactive, pending admin approval
        user.is_active = False
        user.role = User.Role.MEMBER
        user.can_see_all_emails = False
        user.avatar_url = extra_data.get("picture", "")
        user.save(
            update_fields=["is_active", "role", "can_see_all_emails", "avatar_url"]
        )

        # Notify admin
        admin_email = getattr(
            settings, "ADMIN_EMAIL", os.environ.get("ADMIN_EMAIL", "")
        )
        if admin_email:
            try:
                send_mail(
                    subject=f"New user signup: {user.email}",
                    message=(
                        f"{user.get_full_name()} ({user.email}) signed up via "
                        f"Google SSO.\n\nApprove at: "
                        f"https://triage.vidarbhainfotech.com/accounts/team/"
                    ),
                    from_email=None,
                    recipient_list=[admin_email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception(
                    "Failed to send admin notification for new user %s", user.email
                )

        messages.info(request, "Account created. Waiting for admin approval.")
        raise ImmediateHttpResponse(redirect("/accounts/login/?pending=1"))

    def authentication_error(
        self, request, provider_id, error=None, exception=None, extra_context=None
    ):
        """Handle OAuth errors gracefully."""
        logger.error(
            "OAuth error: provider=%s error=%s exception=%s",
            provider_id,
            error,
            exception,
        )
        messages.error(request, "Sign-in failed. Please try again.")
        return redirect("/accounts/login/?error=auth")
