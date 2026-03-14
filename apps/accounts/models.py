"""User model for VIPL Email Agent v2."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role and email visibility fields."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Team Member"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    can_see_all_emails = models.BooleanField(
        default=False,
        help_text="If False, user only sees emails assigned to them",
    )

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
