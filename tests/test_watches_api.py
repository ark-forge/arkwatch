"""Tests for watches API endpoints (CRUD, auth, SSRF, tier limits)"""

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
def isolate_data(tmp_path):
    """Isolate API keys and database to temp files."""
    keys_file = str(tmp_path / "api_keys.json")
    data_dir = str(tmp_path / "data")
    watches_file = f"{data_dir}/watches.json"
    reports_file = f"{data_dir}/reports.json"

    with open(keys_file, "w") as f:
        f.write("{}")

    with (
        patch("src.api.auth.API_KEYS_FILE", keys_file),
        patch("src.storage.database.DATA_DIR", data_dir),
        patch("src.storage.database.WATCHES_FILE", watches_file),
        patch("src.storage.database.REPORTS_FILE", reports_file),
    ):
        # Re-initialize database singleton
        import src.storage.database as db_mod

        db_mod._db = None
        yield
        db_mod._db = None


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from src.api.routers.auth import _registration_attempts, _verify_attempts

    _registration_attempts.clear()
    _verify_attempts.clear()
    yield


def _create_verified_user(client, email="watches@example.com"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Watch Tester", "privacy_accepted": True},
    )
    api_key = resp.json()["api_key"]
    from src.api.auth import regenerate_verification_code

    code = regenerate_verification_code(email)
    client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    return api_key


class TestCreateWatch:
    def test_create_watch(self, client):
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "My Watch"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Watch"
        assert data["url"] == "https://example.com/"
        assert data["status"] == "active"
        assert "id" in data

    def test_create_watch_with_notify_email(self, client):
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "W", "notify_email": "other@example.com"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["notify_email"] == "other@example.com"

    def test_create_watch_default_notify_email(self, client):
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "W"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["notify_email"] == "watches@example.com"

    def test_create_watch_enforces_min_interval(self, client):
        """Free tier minimum interval is 86400 (1 day)."""
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Fast", "check_interval": 60},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["check_interval"] >= 86400


class TestSSRFProtection:
    def test_ssrf_localhost(self, client):
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "http://127.0.0.1:8080/health", "name": "SSRF"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"].lower()

    def test_ssrf_private_ip(self, client):
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "http://192.168.1.1", "name": "SSRF"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 400

    def test_ssrf_10_network(self, client):
        api_key = _create_verified_user(client)
        resp = client.post(
            "/api/v1/watches",
            json={"url": "http://10.0.0.1", "name": "SSRF"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 400


class TestTierLimits:
    def test_free_tier_max_3_watches(self, client):
        api_key = _create_verified_user(client)
        for i in range(3):
            resp = client.post(
                "/api/v1/watches",
                json={"url": f"https://example{i}.com", "name": f"Watch {i}"},
                headers={"X-API-Key": api_key},
            )
            assert resp.status_code == 200

        # 4th should fail
        resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example99.com", "name": "Watch 4"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 403
        assert "limite" in resp.json()["detail"].lower()


class TestListWatches:
    def test_list_empty(self, client):
        api_key = _create_verified_user(client)
        resp = client.get("/api/v1/watches", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_own_watches_only(self, client):
        key1 = _create_verified_user(client, "user1@example.com")
        key2 = _create_verified_user(client, "user2@example.com")

        client.post(
            "/api/v1/watches",
            json={"url": "https://user1.com", "name": "User1 Watch"},
            headers={"X-API-Key": key1},
        )
        client.post(
            "/api/v1/watches",
            json={"url": "https://user2.com", "name": "User2 Watch"},
            headers={"X-API-Key": key2},
        )

        resp1 = client.get("/api/v1/watches", headers={"X-API-Key": key1})
        resp2 = client.get("/api/v1/watches", headers={"X-API-Key": key2})

        assert len(resp1.json()) == 1
        assert resp1.json()[0]["name"] == "User1 Watch"
        assert len(resp2.json()) == 1
        assert resp2.json()[0]["name"] == "User2 Watch"


class TestGetWatch:
    def test_get_own_watch(self, client):
        api_key = _create_verified_user(client)
        create_resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Mine"},
            headers={"X-API-Key": api_key},
        )
        watch_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/watches/{watch_id}", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Mine"

    def test_get_nonexistent_watch(self, client):
        api_key = _create_verified_user(client)
        resp = client.get("/api/v1/watches/nonexistent", headers={"X-API-Key": api_key})
        assert resp.status_code == 404

    def test_get_other_users_watch_denied(self, client):
        key1 = _create_verified_user(client, "owner@example.com")
        key2 = _create_verified_user(client, "intruder@example.com")

        create_resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Private"},
            headers={"X-API-Key": key1},
        )
        watch_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/watches/{watch_id}", headers={"X-API-Key": key2})
        assert resp.status_code == 403


class TestUpdateWatch:
    def test_update_name(self, client):
        api_key = _create_verified_user(client)
        create_resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Old Name"},
            headers={"X-API-Key": api_key},
        )
        watch_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/watches/{watch_id}",
            json={"name": "New Name"},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_other_users_watch_denied(self, client):
        key1 = _create_verified_user(client, "owner2@example.com")
        key2 = _create_verified_user(client, "hacker@example.com")

        create_resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Target"},
            headers={"X-API-Key": key1},
        )
        watch_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/watches/{watch_id}",
            json={"name": "Hacked"},
            headers={"X-API-Key": key2},
        )
        assert resp.status_code == 403


class TestDeleteWatch:
    def test_delete_own_watch(self, client):
        api_key = _create_verified_user(client)
        create_resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "To Delete"},
            headers={"X-API-Key": api_key},
        )
        watch_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/watches/{watch_id}", headers={"X-API-Key": api_key})
        assert resp.status_code == 200

        # Verify it's gone
        resp = client.get(f"/api/v1/watches/{watch_id}", headers={"X-API-Key": api_key})
        assert resp.status_code == 404

    def test_delete_other_users_watch_denied(self, client):
        key1 = _create_verified_user(client, "victim@example.com")
        key2 = _create_verified_user(client, "attacker@example.com")

        create_resp = client.post(
            "/api/v1/watches",
            json={"url": "https://example.com", "name": "Protected"},
            headers={"X-API-Key": key1},
        )
        watch_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/watches/{watch_id}", headers={"X-API-Key": key2})
        assert resp.status_code == 403
