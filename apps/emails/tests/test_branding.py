"""Tests for VIPL branding: logos, favicon, brand colors, page titles."""
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client


@pytest.fixture
def auth_client(db):
    from apps.accounts.models import User

    user = User.objects.create_user(
        username="brandtest",
        password="brandtest123",
        email="brandtest@vidarbhainfotech.com",
        is_staff=True,
        role="admin",
    )
    client = Client()
    client.login(username="brandtest", password="brandtest123")
    return client


def test_static_assets_exist():
    """All logo files and favicon must exist on disk."""
    static_dir = settings.BASE_DIR / "static" / "img"
    assert (static_dir / "vipl-icon.jpg").exists(), "vipl-icon.jpg missing"
    assert (static_dir / "vipl-logo-full.jpg").exists(), "vipl-logo-full.jpg missing"
    assert (static_dir / "favicon.ico").exists(), "favicon.ico missing"


@pytest.mark.django_db
def test_sidebar_contains_logo(auth_client):
    """Sidebar must render the Vi mark logo."""
    resp = auth_client.get("/emails/")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "vipl-icon" in html, "Sidebar missing vipl-icon reference"


@pytest.mark.django_db
def test_login_contains_logo():
    """Login page must show the full VIPL logo."""
    client = Client()
    resp = client.get("/accounts/login/")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "vipl-logo-full" in html, "Login page missing vipl-logo-full reference"


def test_no_indigo_in_templates():
    """No template file should contain the word 'indigo' (brand color replaced)."""
    templates_dir = settings.BASE_DIR / "templates"
    pattern = re.compile(r"\bindigo\b")
    violations = []
    for html_file in templates_dir.rglob("*.html"):
        if "inspect.html" in html_file.name:
            continue
        content = html_file.read_text()
        matches = pattern.findall(content)
        if matches:
            violations.append(f"{html_file.relative_to(templates_dir)}: {len(matches)} occurrences")
    assert not violations, f"indigo found in templates:\n" + "\n".join(violations)


def test_no_violet_in_brand_templates():
    """No template file should contain the word 'violet' (brand color replaced)."""
    templates_dir = settings.BASE_DIR / "templates"
    pattern = re.compile(r"\bviolet\b")
    violations = []
    for html_file in templates_dir.rglob("*.html"):
        if "inspect.html" in html_file.name:
            continue
        content = html_file.read_text()
        matches = pattern.findall(content)
        if matches:
            violations.append(f"{html_file.relative_to(templates_dir)}: {len(matches)} occurrences")
    assert not violations, f"violet found in templates:\n" + "\n".join(violations)


@pytest.mark.django_db
def test_page_titles_contain_vipl(auth_client):
    """Page titles must follow 'VIPL Triage' format."""
    resp = auth_client.get("/emails/")
    html = resp.content.decode()
    assert "VIPL Triage" in html, "Page title missing 'VIPL Triage'"


@pytest.mark.django_db
class TestPageTitleConsistency:
    """Every page must follow 'VIPL Triage | {Page Name}' title pattern."""

    def test_inbox_title(self, auth_client):
        resp = auth_client.get("/emails/")
        assert "VIPL Triage | Inbox" in resp.content.decode()

    def test_activity_title(self, auth_client):
        resp = auth_client.get("/emails/activity/")
        assert "VIPL Triage | Activity" in resp.content.decode()

    def test_settings_title(self, auth_client):
        resp = auth_client.get("/emails/settings/")
        assert "VIPL Triage | Settings" in resp.content.decode()

    def test_team_title(self, auth_client):
        resp = auth_client.get("/accounts/team/")
        assert "VIPL Triage | Team" in resp.content.decode()

    def test_inspect_title(self):
        client = Client()
        resp = client.get("/emails/inspect/")
        assert "VIPL Triage | Dev Inspector" in resp.content.decode()

    def test_login_title(self):
        client = Client()
        resp = client.get("/accounts/login/")
        assert "VIPL Triage" in resp.content.decode()


@pytest.mark.django_db
def test_favicon_link_in_base(auth_client):
    """Base template must include a favicon link."""
    resp = auth_client.get("/emails/")
    html = resp.content.decode()
    assert "favicon" in html, "Base template missing favicon link"
