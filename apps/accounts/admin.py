"""Custom UserAdmin for VIPL Email Agent v2."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model with role and visibility fields."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "can_see_all_emails",
        "is_staff",
        "is_active",
    )
    list_filter = BaseUserAdmin.list_filter + ("role", "can_see_all_emails")

    # Add role and can_see_all_emails to the edit form
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "VIPL Settings",
            {
                "fields": ("role", "can_see_all_emails"),
            },
        ),
    )

    # Add role and can_see_all_emails to the create form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "VIPL Settings",
            {
                "fields": ("role", "can_see_all_emails"),
            },
        ),
    )
