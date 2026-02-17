"""Tests for reports API endpoints"""

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


def _create_verified_user(client, email="reports@example.com"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Report Tester", "privacy_accepted": True},
    )
    api_key = resp.json()["api_key"]
    from src.api.auth import regenerate_verification_code

    code = regenerate_verification_code(email)
    client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    return api_key


def _create_watch_and_report(client, api_key):
    """Create a watch and manually add a report for it."""
    resp = client.post(
        "/api/v1/watches",
        json={"url": "https://example.com", "name": "Reported Watch"},
        headers={"X-API-Key": api_key},
    )
    watch_id = resp.json()["id"]

    from src.storage import get_db

    db = get_db()
    report = db.create_report(
        watch_id=watch_id,
        changes_detected=True,
        current_hash="abc123",
        previous_hash="xyz789",
        diff="-old\n+new",
        ai_summary="Content changed",
        ai_importance="medium",
    )
    return watch_id, report["id"]


class TestListReports:
    def test_list_reports_empty(self, client):
        api_key = _create_verified_user(client)
        resp = client.get("/api/v1/reports", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_own_reports(self, client):
        api_key = _create_verified_user(client)
        _create_watch_and_report(client, api_key)

        resp = client.get("/api/v1/reports", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["changes_detected"] is True

    def test_list_reports_filtered_by_watch(self, client):
        api_key = _create_verified_user(client)
        watch_id, _ = _create_watch_and_report(client, api_key)

        resp = client.get(f"/api/v1/reports?watch_id={watch_id}", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_reports_no_access_to_others(self, client):
        key1 = _create_verified_user(client, "reporter1@example.com")
        key2 = _create_verified_user(client, "reporter2@example.com")

        _create_watch_and_report(client, key1)

        resp = client.get("/api/v1/reports", headers={"X-API-Key": key2})
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_reports_unauthenticated(self, client):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 401


class TestGetReport:
    def test_get_own_report(self, client):
        api_key = _create_verified_user(client)
        _, report_id = _create_watch_and_report(client, api_key)

        resp = client.get(f"/api/v1/reports/{report_id}", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert resp.json()["id"] == report_id
        assert resp.json()["ai_summary"] == "Content changed"

    def test_get_nonexistent_report(self, client):
        api_key = _create_verified_user(client)
        resp = client.get("/api/v1/reports/nonexistent", headers={"X-API-Key": api_key})
        assert resp.status_code == 404

    def test_get_other_users_report_denied(self, client):
        key1 = _create_verified_user(client, "owner3@example.com")
        key2 = _create_verified_user(client, "snooper@example.com")

        _, report_id = _create_watch_and_report(client, key1)

        resp = client.get(f"/api/v1/reports/{report_id}", headers={"X-API-Key": key2})
        assert resp.status_code == 403

    def test_filter_by_other_users_watch_denied(self, client):
        key1 = _create_verified_user(client, "filterowner@example.com")
        key2 = _create_verified_user(client, "filterhacker@example.com")

        watch_id, _ = _create_watch_and_report(client, key1)

        resp = client.get(f"/api/v1/reports?watch_id={watch_id}", headers={"X-API-Key": key2})
        assert resp.status_code == 403
