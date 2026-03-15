"""User model for VIPL Email Agent v2."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role and email visibility fields."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TRIAGE_LEAD = "triage_lead", "Triage Lead"
        MEMBER = "member", "Team Member"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    can_see_all_emails = models.BooleanField(
        default=False,
        help_text="If False, user only sees emails assigned to them",
    )
    avatar_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Google profile photo URL, updated on each login",
    )

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_triage_lead(self):
        """True if user has the Triage Lead role."""
        return self.role == self.Role.TRIAGE_LEAD

    @property
    def can_assign(self):
        """Admin and Triage Lead can assign/reassign threads."""
        return self.role in (self.Role.ADMIN, self.Role.TRIAGE_LEAD) or self.is_staff

    @property
    def is_admin_only(self):
        """Only admin: settings write, role management, force poll."""
        return self.role == self.Role.ADMIN or self.is_staff

    @property
    def can_triage(self):
        """Admin and Triage Lead: mark irrelevant, bulk actions."""
        return self.can_assign

    @property
    def can_approve_users(self):
        """Admin and Triage Lead: approve pending users on team page."""
        return self.role in (self.Role.ADMIN, self.Role.TRIAGE_LEAD) or self.is_staff
