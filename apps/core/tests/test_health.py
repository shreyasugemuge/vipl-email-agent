import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.core.models import SystemConfig


@pytest.mark.django_db
class TestHealthEndpointUnauthenticated:
    """Unauthenticated requests get minimal health response."""

    def test_health_returns_200(self, client):
        response = client.get("/health/")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health/")
        assert response["Content-Type"] == "application/json"

    def test_health_unauthenticated_returns_minimal(self, client):
        """Unauthenticated requests get only {status: ...}."""
        response = client.get("/health/")
        data = json.loads(response.content)
        assert "status" in data
        assert "version" not in data
        assert "database" not in data
        assert "scheduler" not in data


@pytest.mark.django_db
class TestHealthEndpointAdmin:
    """Authenticated admin requests get full health details."""

    @pytest.fixture(autouse=True)
    def _setup(self, client, admin_user):
        """Log in admin user and clean up heartbeat state for each test."""
        SystemConfig.objects.filter(key="scheduler_heartbeat").delete()
        client.force_login(admin_user)
        self._client = client

    def test_health_contains_required_fields(self):
        response = self._client.get("/health/")
        data = json.loads(response.content)
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "database" in data
        assert "scheduler" in data

    def test_health_status_healthy_when_db_connected(self):
        response = self._client.get("/health/")
        data = json.loads(response.content)
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_health_uptime_is_non_negative(self):
        response = self._client.get("/health/")
        data = json.loads(response.content)
        assert data["uptime_seconds"] >= 0

    def test_scheduler_not_started_when_no_heartbeat(self):
        """No heartbeat = scheduler not started yet (healthy, not degraded)."""
        response = self._client.get("/health/")
        data = json.loads(response.content)
        assert data["scheduler"] == "not_started"
        assert data["status"] == "healthy"

    def test_scheduler_running_with_fresh_heartbeat(self):
        """Fresh heartbeat = scheduler running."""
        SystemConfig.objects.update_or_create(
            key="scheduler_heartbeat",
            defaults={
                "value": timezone.now().isoformat(),
                "value_type": "str",
            },
        )
        response = self._client.get("/health/")
        data = json.loads(response.content)
        assert data["scheduler"] == "running"
        assert data["status"] == "healthy"

    def test_scheduler_stale_with_old_heartbeat(self):
        """Old heartbeat = scheduler stale = degraded."""
        old_time = timezone.now() - timezone.timedelta(minutes=10)
        SystemConfig.objects.update_or_create(
            key="scheduler_heartbeat",
            defaults={
                "value": old_time.isoformat(),
                "value_type": "str",
            },
        )
        response = self._client.get("/health/")
        data = json.loads(response.content)
        assert data["scheduler"] == "stale"
        assert data["status"] == "degraded"
