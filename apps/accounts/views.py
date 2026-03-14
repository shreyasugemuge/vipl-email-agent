"""Authentication views for VIPL Email Agent v2.

DashboardView removed in Phase 4.5 (dead code -- root RedirectView
at /accounts/dashboard/ intercepts before this module's URL is reached).
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import User


@require_http_methods(["GET", "POST"])
def dev_login(request):
    """Quick login for local development only. Disabled when DEBUG=False."""
    if not settings.DEBUG:
        return redirect("login")

    if request.method == "POST":
        role = request.POST.get("role", "member")
        username = f"dev-{role}"
        email = f"{username}@vidarbhainfotech.com"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": role.title(),
                "last_name": "User",
                "role": role,
                "is_active": True,
                "is_staff": role == "admin",
                "can_see_all_emails": role == "admin",
            },
        )
        if not created:
            # Ensure existing dev user has correct role settings
            user.role = role
            user.is_staff = role == "admin"
            user.can_see_all_emails = role == "admin"
            user.save(update_fields=["role", "is_staff", "can_see_all_emails"])

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Dev login as {role}")
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, "registration/dev_login.html")
