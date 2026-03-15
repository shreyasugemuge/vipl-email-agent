import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.core.models import SystemConfig


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health/")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health/")
        assert response["Content-Type"] == "application/json"

    def test_health_unauthenticated_returns_minimal(self, client):
        """Unauthenticated requests only get status field."""
        response = client.get("/health/")
        data = json.loads(response.content)
        assert "status" in data
        assert "version" not in data
        assert "database" not in data

    def test_health_contains_required_fields(self, client, admin_user):
        """Staff users get full details."""
        client.force_login(admin_user)
        response = client.get("/health/")
        data = json.loads(response.content)
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "database" in data
        assert "scheduler" in data

    def test_health_status_healthy_when_db_connected(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_health_uptime_is_non_negative(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["uptime_seconds"] >= 0

    def test_scheduler_not_started_when_no_heartbeat(self, client, admin_user):
        """No heartbeat = scheduler not started yet (healthy, not degraded)."""
        client.force_login(admin_user)
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["scheduler"] == "not_started"
        assert data["status"] == "healthy"

    def test_scheduler_running_with_fresh_heartbeat(self, client, admin_user):
        """Fresh heartbeat = scheduler running."""
        SystemConfig.objects.update_or_create(
            key="scheduler_heartbeat",
            defaults={
                "value": timezone.now().isoformat(),
                "value_type": "str",
            },
        )
        client.force_login(admin_user)
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["scheduler"] == "running"
        assert data["status"] == "healthy"

    def test_scheduler_stale_with_old_heartbeat(self, client, admin_user):
        """Old heartbeat = scheduler stale = degraded."""
        old_time = timezone.now() - timezone.timedelta(minutes=10)
        SystemConfig.objects.update_or_create(
            key="scheduler_heartbeat",
            defaults={
                "value": old_time.isoformat(),
                "value_type": "str",
            },
        )
        client.force_login(admin_user)
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["scheduler"] == "stale"
        assert data["status"] == "degraded"
