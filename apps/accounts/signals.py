"""Signals for VIPL accounts app."""

from django.contrib.auth.signals import user_logged_in


def on_user_logged_in(sender, request, user, **kwargs):
    """Show welcome toast on login (once per session)."""
    try:
        if not request.session.get("_welcome_shown"):
            from django.contrib import messages

            first_name = user.first_name or user.username
            messages.info(request, f"Welcome, {first_name}!")
            request.session["_welcome_shown"] = True
    except Exception:
        pass  # Gracefully handle missing messages middleware (e.g. in tests)


user_logged_in.connect(on_user_logged_in)
