"""Tests for the database module"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

import sys
sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch")


class TestDatabase:
    """Tests for Database class"""

    @pytest.fixture
    def db_with_temp_dir(self, tmp_path):
        """Create a Database with temporary directory"""
        data_dir = str(tmp_path / "data")
        watches_file = f"{data_dir}/watches.json"
        reports_file = f"{data_dir}/reports.json"

        with patch("src.storage.database.DATA_DIR", data_dir), \
             patch("src.storage.database.WATCHES_FILE", watches_file), \
             patch("src.storage.database.REPORTS_FILE", reports_file):
            from src.storage.database import Database
            db = Database()
            yield db

    def test_init_creates_files(self, db_with_temp_dir, tmp_path):
        """Test that init creates necessary files"""
        data_dir = tmp_path / "data"
        assert (data_dir / "watches.json").exists()
        assert (data_dir / "reports.json").exists()

    def test_create_watch(self, db_with_temp_dir, sample_watch):
        """Test creating a watch"""
        db = db_with_temp_dir
        watch = db.create_watch(**sample_watch)

        assert watch["name"] == "Test Watch"
        assert watch["url"] == "https://example.com"
        assert watch["status"] == "active"
        assert "id" in watch
        assert watch["last_check"] is None

    def test_get_watches_all(self, db_with_temp_dir, sample_watch):
        """Test getting all watches"""
        db = db_with_temp_dir
        db.create_watch(**sample_watch)
        db.create_watch(name="Watch 2", url="https://test.com")

        watches = db.get_watches()
        assert len(watches) == 2

    def test_get_watches_by_status(self, db_with_temp_dir, sample_watch):
        """Test filtering watches by status"""
        db = db_with_temp_dir
        watch = db.create_watch(**sample_watch)
        db.update_watch(watch["id"], status="paused")
        db.create_watch(name="Active Watch", url="https://active.com")

        active = db.get_watches(status="active")
        paused = db.get_watches(status="paused")

        assert len(active) == 1
        assert len(paused) == 1
        assert active[0]["name"] == "Active Watch"

    def test_get_watch_by_id(self, db_with_temp_dir, sample_watch):
        """Test getting a specific watch by ID"""
        db = db_with_temp_dir
        created = db.create_watch(**sample_watch)

        watch = db.get_watch(created["id"])
        assert watch is not None
        assert watch["name"] == "Test Watch"

    def test_get_watch_not_found(self, db_with_temp_dir):
        """Test getting non-existent watch"""
        db = db_with_temp_dir
        watch = db.get_watch("non-existent-id")
        assert watch is None

    def test_update_watch(self, db_with_temp_dir, sample_watch):
        """Test updating a watch"""
        db = db_with_temp_dir
        created = db.create_watch(**sample_watch)

        updated = db.update_watch(created["id"], name="Updated Name", status="paused")

        assert updated["name"] == "Updated Name"
        assert updated["status"] == "paused"
        assert updated["url"] == sample_watch["url"]  # Unchanged

    def test_update_watch_not_found(self, db_with_temp_dir):
        """Test updating non-existent watch"""
        db = db_with_temp_dir
        result = db.update_watch("non-existent-id", name="Test")
        assert result is None

    def test_delete_watch(self, db_with_temp_dir, sample_watch):
        """Test deleting a watch"""
        db = db_with_temp_dir
        created = db.create_watch(**sample_watch)

        result = db.delete_watch(created["id"])
        assert result is True

        watch = db.get_watch(created["id"])
        assert watch is None

    def test_delete_watch_not_found(self, db_with_temp_dir):
        """Test deleting non-existent watch"""
        db = db_with_temp_dir
        result = db.delete_watch("non-existent-id")
        assert result is False


class TestReports:
    """Tests for report operations"""

    @pytest.fixture
    def db_with_temp_dir(self, tmp_path):
        """Create a Database with temporary directory"""
        data_dir = str(tmp_path / "data")
        watches_file = f"{data_dir}/watches.json"
        reports_file = f"{data_dir}/reports.json"

        with patch("src.storage.database.DATA_DIR", data_dir), \
             patch("src.storage.database.WATCHES_FILE", watches_file), \
             patch("src.storage.database.REPORTS_FILE", reports_file):
            from src.storage.database import Database
            db = Database()
            yield db

    def test_create_report(self, db_with_temp_dir):
        """Test creating a report"""
        db = db_with_temp_dir
        report = db.create_report(
            watch_id="test-watch-id",
            changes_detected=True,
            current_hash="abc123",
            previous_hash="xyz789",
            diff="-old\n+new",
            ai_summary="Content updated",
            ai_importance="high"
        )

        assert report["watch_id"] == "test-watch-id"
        assert report["changes_detected"] is True
        assert report["ai_importance"] == "high"
        assert report["notified"] is False
        assert "id" in report

    def test_create_report_no_changes(self, db_with_temp_dir):
        """Test creating a report with no changes"""
        db = db_with_temp_dir
        report = db.create_report(
            watch_id="test-watch-id",
            changes_detected=False,
            current_hash="abc123"
        )

        assert report["changes_detected"] is False
        assert report["previous_hash"] is None
        assert report["diff"] is None

    def test_get_reports_all(self, db_with_temp_dir):
        """Test getting all reports"""
        db = db_with_temp_dir
        db.create_report("watch-1", False, "hash1")
        db.create_report("watch-2", True, "hash2")

        reports = db.get_reports()
        assert len(reports) == 2

    def test_get_reports_by_watch(self, db_with_temp_dir):
        """Test filtering reports by watch_id"""
        db = db_with_temp_dir
        db.create_report("watch-1", False, "hash1")
        db.create_report("watch-1", True, "hash2")
        db.create_report("watch-2", False, "hash3")

        reports = db.get_reports(watch_id="watch-1")
        assert len(reports) == 2
        assert all(r["watch_id"] == "watch-1" for r in reports)

    def test_get_reports_limit(self, db_with_temp_dir):
        """Test reports limit"""
        db = db_with_temp_dir
        for i in range(10):
            db.create_report(f"watch-{i}", False, f"hash{i}")

        reports = db.get_reports(limit=5)
        assert len(reports) == 5

    def test_mark_report_notified(self, db_with_temp_dir):
        """Test marking a report as notified"""
        db = db_with_temp_dir
        report = db.create_report("watch-1", True, "hash1")

        result = db.mark_report_notified(report["id"])
        assert result is True

        reports = db.get_reports()
        notified_report = next(r for r in reports if r["id"] == report["id"])
        assert notified_report["notified"] is True

    def test_mark_report_notified_not_found(self, db_with_temp_dir):
        """Test marking non-existent report as notified"""
        db = db_with_temp_dir
        result = db.mark_report_notified("non-existent-id")
        assert result is False
