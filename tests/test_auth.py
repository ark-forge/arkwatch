"""Tests for authentication endpoints (register, verify, RGPD)"""

import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch")

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def isolate_api_keys(tmp_path):
    """Isolate API keys to a temp file for each test."""
    keys_file = str(tmp_path / "api_keys.json")
    with open(keys_file, "w") as f:
        f.write("{}")
    with patch("src.api.auth.API_KEYS_FILE", keys_file):
        yield


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear in-memory rate limits between tests."""
    from src.api.routers.auth import _registration_attempts, _verify_attempts

    _registration_attempts.clear()
    _verify_attempts.clear()
    yield
    _registration_attempts.clear()
    _verify_attempts.clear()


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "name": "Test User", "privacy_accepted": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user@example.com"
        assert data["name"] == "Test User"
        assert data["tier"] == "free"
        assert data["api_key"].startswith("ak_")

    def test_register_missing_name(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "privacy_accepted": True},
        )
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-email", "name": "Test", "privacy_accepted": True},
        )
        assert resp.status_code == 422

    def test_register_privacy_not_accepted(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "name": "Test", "privacy_accepted": False},
        )
        assert resp.status_code == 422

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@example.com", "name": "User", "privacy_accepted": True}
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_short_name(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "name": "X", "privacy_accepted": True},
        )
        assert resp.status_code == 400

    def test_register_returns_privacy_policy_url(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "pp@example.com", "name": "Test", "privacy_accepted": True},
        )
        assert resp.json()["privacy_policy"] == "https://arkforge.fr/privacy"


class TestVerifyEmail:
    def _register(self, client, email="verify@example.com"):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "name": "Verifier", "privacy_accepted": True},
        )
        return resp.json()["api_key"]

    def test_verify_wrong_code(self, client):
        self._register(client)
        resp = client.post(
            "/api/v1/auth/verify-email",
            json={"email": "verify@example.com", "code": "000000"},
        )
        assert resp.status_code == 400

    def test_verify_nonexistent_email(self, client):
        resp = client.post(
            "/api/v1/auth/verify-email",
            json={"email": "noone@example.com", "code": "123456"},
        )
        assert resp.status_code == 400

    def test_verify_correct_code(self, client):
        """Verify with the correct code by reading it from the keys file."""
        self._register(client)
        # Get the verification code by regenerating it
        from src.api.auth import regenerate_verification_code

        code = regenerate_verification_code("verify@example.com")
        assert code is not None

        resp = client.post(
            "/api/v1/auth/verify-email",
            json={"email": "verify@example.com", "code": code},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "verified"

    def test_verified_user_can_create_watch(self, client):
        api_key = self._register(client)
        from src.api.auth import regenerate_verification_code

        code = regenerate_verification_code("verify@example.com")
        client.post("/api/v1/auth/verify-email", json={"email": "verify@example.com", "code": code})

        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "My Watch"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200


class TestResendVerification:
    def test_resend_always_returns_success(self, client):
        """Resend always returns success to prevent email enumeration."""
        resp = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"


class TestAccountRGPD:
    def _create_verified_user(self, client, email="rgpd@example.com"):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "name": "RGPD User", "privacy_accepted": True},
        )
        api_key = resp.json()["api_key"]
        from src.api.auth import regenerate_verification_code

        code = regenerate_verification_code(email)
        client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
        return api_key

    def test_export_data_art15(self, client):
        api_key = self._create_verified_user(client)
        resp = client.get("/api/v1/auth/account/data", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        data = resp.json()
        assert "account" in data
        assert "watches" in data
        assert "reports" in data
        assert data["account"]["email"] == "rgpd@example.com"

    def test_update_account_art16(self, client):
        api_key = self._create_verified_user(client)
        resp = client.patch(
            "/api/v1/auth/account",
            json={"name": "New Name"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert "name" in resp.json()["updated_fields"]

    def test_update_account_no_fields(self, client):
        api_key = self._create_verified_user(client)
        resp = client.patch(
            "/api/v1/auth/account",
            json={},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 400

    def test_delete_account_art17(self, client):
        api_key = self._create_verified_user(client)
        # Create a watch first
        client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "To Delete"},
            headers={"X-API-Key": api_key},
        )

        resp = client.delete("/api/v1/auth/account", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        assert resp.json()["data_deleted"]["watches_deleted"] >= 1

        # Key should be invalid now
        resp = client.get("/api/v1/watches", headers={"X-API-Key": api_key})
        assert resp.status_code == 401


class TestAuthentication:
    def test_no_api_key(self, client):
        resp = client.get("/api/v1/watches")
        assert resp.status_code == 401

    def test_invalid_api_key(self, client):
        resp = client.get("/api/v1/watches", headers={"X-API-Key": "ak_invalid"})
        assert resp.status_code == 401

    def test_unverified_user_cannot_create_watch(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "unverified@example.com", "name": "Unverified", "privacy_accepted": True},
        )
        api_key = resp.json()["api_key"]
        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Test"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 403

    def test_unverified_user_can_list_watches(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "list@example.com", "name": "Lister", "privacy_accepted": True},
        )
        api_key = resp.json()["api_key"]
        resp = client.get("/api/v1/watches", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
