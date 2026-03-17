"""Authentication and team management views for VIPL Email Agent v2."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.emails.models import (
    ActivityLog, AssignmentRule, CategoryVisibility, Thread, ThreadViewer,
)
from apps.emails.services.dtos import VALID_CATEGORIES

from .models import User


# ---------------------------------------------------------------------------
# Dev login (DEBUG only)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Team management (admin only)
# ---------------------------------------------------------------------------


def _require_admin(user):
    return user.is_staff or user.role == User.Role.ADMIN


@login_required
def team_list(request):
    """Team management page — list all users, approve/deny, set roles and categories."""
    if not request.user.can_approve_users:
        return HttpResponseForbidden("Admin access required.")

    users = list(User.objects.all().order_by("is_active", "-role", "first_name", "username"))

    # Annotate each user with their visible categories
    for u in users:
        u.user_cats = set(
            CategoryVisibility.objects.filter(user=u).values_list("category", flat=True)
        )

    stats = {
        "total": len(users),
        "active": sum(1 for u in users if u.is_active),
        "pending": sum(1 for u in users if not u.is_active),
        "admins": sum(1 for u in users if u.role == User.Role.ADMIN),
    }

    context = {
        "team_users": users,
        "stats": stats,
        "valid_categories": VALID_CATEGORIES,
    }
    return render(request, "accounts/team.html", context)


@login_required
@require_POST
def toggle_active(request, pk):
    """Activate or deactivate a user. Admin and Triage Lead."""
    if not request.user.can_approve_users:
        return HttpResponseForbidden("Admin access required.")

    target = get_object_or_404(User, pk=pk)

    if target == request.user:
        return HttpResponseForbidden("Cannot deactivate yourself.")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    # On deactivation: unassign open threads, remove rules, clear viewers
    if not target.is_active:
        open_threads = Thread.objects.filter(
            assigned_to=target,
            status__in=["new", "acknowledged", "reopened"],
        )
        thread_count = open_threads.count()
        target_name = target.get_full_name() or target.username

        # Log each unassignment
        for thread in open_threads:
            ActivityLog.objects.create(
                thread=thread,
                user=request.user,
                action="unassigned",
                old_value=target_name,
                new_value="",
                detail=f"User {target_name} deactivated",
            )

        # Bulk unassign
        open_threads.update(assigned_to=None, assigned_by=None, status="new")

        # Remove assignment rules and viewer records
        AssignmentRule.objects.filter(assignee=target).delete()
        ThreadViewer.objects.filter(user=target).delete()

    return _render_user_row(request, target)


@login_required
@require_POST
def change_role(request, pk):
    """Change a user's role. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    target = get_object_or_404(User, pk=pk)
    new_role = request.POST.get("role", "")

    if new_role not in dict(User.Role.choices):
        return HttpResponseForbidden("Invalid role.")

    if target == request.user and new_role != User.Role.ADMIN:
        return HttpResponseForbidden("Cannot remove your own admin role.")

    target.role = new_role
    target.is_staff = (new_role == User.Role.ADMIN)
    target.save(update_fields=["role", "is_staff"])

    return _render_user_row(request, target)


@login_required
@require_POST
def toggle_visibility(request, pk):
    """Toggle can_see_all_emails for a user. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    target = get_object_or_404(User, pk=pk)
    target.can_see_all_emails = not target.can_see_all_emails
    target.save(update_fields=["can_see_all_emails"])

    return _render_user_row(request, target)


@login_required
@require_POST
def save_categories(request, pk):
    """Save category visibility for a user. Admin only."""
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")

    target = get_object_or_404(User, pk=pk)
    categories = request.POST.getlist("categories")

    CategoryVisibility.objects.filter(user=target).delete()
    CategoryVisibility.objects.bulk_create([
        CategoryVisibility(user=target, category=cat)
        for cat in categories
        if cat in VALID_CATEGORIES
    ])

    return _render_user_row(request, target)


def _render_user_row(request, target):
    """Render _user_row.html partial with user's visible categories annotated."""
    target.user_cats = set(
        CategoryVisibility.objects.filter(user=target).values_list("category", flat=True)
    )
    return render(request, "accounts/_user_row.html", {
        "u": target,
        "request_user": request.user,
        "valid_categories": VALID_CATEGORIES,
    })
