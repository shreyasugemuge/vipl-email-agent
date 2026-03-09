"""Shared test fixtures for VIPL Email Agent v2."""

import pytest
from django.test import Client


@pytest.fixture
def admin_user(db):
    """Create an admin user (role=admin, is_staff=True)."""
    from apps.accounts.models import User

    return User.objects.create_user(
        username="admin",
        password="testpass123",
        email="admin@vidarbhainfotech.com",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def member_user(db):
    """Create a team member user (role=member)."""
    from apps.accounts.models import User

    return User.objects.create_user(
        username="member",
        password="testpass123",
        email="member@vidarbhainfotech.com",
        role=User.Role.MEMBER,
    )


@pytest.fixture
def client():
    """Django test client."""
    return Client()
