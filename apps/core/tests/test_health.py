import json

import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health/")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health/")
        assert response["Content-Type"] == "application/json"

    def test_health_contains_required_fields(self, client):
        response = client.get("/health/")
        data = json.loads(response.content)
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "database" in data

    def test_health_status_healthy_when_db_connected(self, client):
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_health_uptime_is_non_negative(self, client):
        response = client.get("/health/")
        data = json.loads(response.content)
        assert data["uptime_seconds"] >= 0
