"""Tests for API health endpoints"""

import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch")

from src.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_health_endpoint(self, client):
        """Test /health endpoint returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ready_endpoint(self, client):
        """Test /ready endpoint returns ready status"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_health_method_not_allowed(self, client):
        """Test /health rejects POST"""
        response = client.post("/health")
        assert response.status_code == 405

    def test_ready_method_not_allowed(self, client):
        """Test /ready rejects POST"""
        response = client.post("/ready")
        assert response.status_code == 405


class TestAPIBasics:
    """Tests for basic API functionality"""

    def test_root_docs_disabled_in_production(self, client):
        """Test API docs are disabled in production (security hardening H2)"""
        response = client.get("/docs")
        assert response.status_code == 404

    def test_openapi_schema_disabled_in_production(self, client):
        """Test OpenAPI schema is disabled in production (security hardening H2)"""
        response = client.get("/openapi.json")
        assert response.status_code == 404
