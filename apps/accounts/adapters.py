"""Custom allauth adapter for VIPL Email Agent.

Enforces @vidarbhainfotech.com domain server-side and auto-creates
new Google users as inactive pending admin approval.
"""

import logging
import os

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect

logger = logging.getLogger(__name__)
ALLOWED_DOMAIN = "vidarbhainfotech.com"


class VIPLSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Domain-locked Google OAuth adapter for VIPL."""

    def pre_social_login(self, request, sociallogin):
        """Enforce @vidarbhainfotech.com domain. Reject all others."""
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

        # If user exists and is linked, update avatar and add welcome message
        if sociallogin.is_existing:
            user = sociallogin.user
            picture = extra_data.get("picture", "")
            if picture and user.avatar_url != picture:
                user.avatar_url = picture
                user.save(update_fields=["avatar_url"])
            # Welcome message for returning users
            first_name = user.first_name or user.username
            messages.info(request, f"Welcome, {first_name}!")

    def save_user(self, request, sociallogin, form=None):
        """Auto-create new Google users as inactive MEMBER."""
        user = super().save_user(request, sociallogin, form)
        extra_data = sociallogin.account.extra_data

        # Set VIPL defaults
        user.is_active = False  # Requires admin approval
        user.role = "member"
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
                        f"Google SSO.\n\nApprove in Django admin: set is_active=True."
                    ),
                    from_email=None,  # Uses DEFAULT_FROM_EMAIL
                    recipient_list=[admin_email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception(
                    "Failed to send admin notification for new user %s", user.email
                )

        # Redirect inactive user to login with message
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
