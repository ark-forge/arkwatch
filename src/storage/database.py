"""Database connection and operations"""

import json
import os
from datetime import datetime
from uuid import uuid4

from ..crypto import decrypt_pii, encrypt_pii

# For MVP, we use a simple JSON file storage
# Will be replaced by PostgreSQL for production

DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
WATCHES_FILE = f"{DATA_DIR}/watches.json"
REPORTS_FILE = f"{DATA_DIR}/reports.json"

# PII fields in watches that must be encrypted at rest
_WATCH_PII_FIELDS = ("notify_email", "user_email")


class Database:
    """Simple JSON-based database for MVP"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._init_files()

    def _init_files(self):
        for f in [WATCHES_FILE, REPORTS_FILE]:
            if not os.path.exists(f):
                with open(f, "w") as fp:
                    json.dump([], fp)

    def _decrypt_watch(self, watch: dict) -> dict:
        """Decrypt PII fields in a watch record."""
        result = dict(watch)
        for field in _WATCH_PII_FIELDS:
            if field in result and result[field] and isinstance(result[field], str):
                result[field] = decrypt_pii(result[field])
        return result

    def _encrypt_watch(self, watch: dict) -> dict:
        """Encrypt PII fields in a watch record."""
        result = dict(watch)
        for field in _WATCH_PII_FIELDS:
            if field in result and result[field] and isinstance(result[field], str):
                result[field] = encrypt_pii(result[field])
        return result

    def _load(self, filepath: str) -> list:
        with open(filepath) as f:
            data = json.load(f)
        # Decrypt PII in watch records
        if filepath == WATCHES_FILE:
            return [self._decrypt_watch(w) for w in data]
        return data

    def _save(self, filepath: str, data: list):
        # Encrypt PII in watch records before saving
        if filepath == WATCHES_FILE:
            data = [self._encrypt_watch(w) for w in data]
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # Watches
    def create_watch(
        self,
        name: str,
        url: str,
        check_interval: int = 3600,
        notify_email: str | None = None,
        min_change_ratio: float | None = None,
    ) -> dict:
        watches = self._load(WATCHES_FILE)
        watch = {
            "id": str(uuid4()),
            "name": name,
            "url": url,
            "check_interval": check_interval,
            "min_change_ratio": min_change_ratio,
            "notify_email": notify_email,
            "status": "active",
            "last_check": None,
            "last_content_hash": None,
            "last_content": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        watches.append(watch)
        self._save(WATCHES_FILE, watches)
        return watch

    def get_watches(self, status: str | None = None) -> list:
        watches = self._load(WATCHES_FILE)
        if status:
            return [w for w in watches if w["status"] == status]
        return watches

    def get_watches_by_user(self, email: str) -> list:
        watches = self._load(WATCHES_FILE)
        return [w for w in watches if w.get("user_email") == email]

    def get_watch(self, watch_id: str) -> dict | None:
        watches = self._load(WATCHES_FILE)
        for w in watches:
            if w["id"] == watch_id:
                return w
        return None

    def update_watch(self, watch_id: str, **kwargs) -> dict | None:
        watches = self._load(WATCHES_FILE)
        for i, w in enumerate(watches):
            if w["id"] == watch_id:
                w.update(kwargs)
                w["updated_at"] = datetime.utcnow().isoformat()
                watches[i] = w
                self._save(WATCHES_FILE, watches)
                return w
        return None

    def delete_watch(self, watch_id: str) -> bool:
        watches = self._load(WATCHES_FILE)
        new_watches = [w for w in watches if w["id"] != watch_id]
        if len(new_watches) < len(watches):
            self._save(WATCHES_FILE, new_watches)
            return True
        return False

    # Reports
    def create_report(
        self,
        watch_id: str,
        changes_detected: bool,
        current_hash: str,
        previous_hash: str | None = None,
        diff: str | None = None,
        ai_summary: str | None = None,
        ai_importance: str | None = None,
    ) -> dict:
        reports = self._load(REPORTS_FILE)
        report = {
            "id": str(uuid4()),
            "watch_id": watch_id,
            "changes_detected": changes_detected,
            "previous_hash": previous_hash,
            "current_hash": current_hash,
            "diff": diff,
            "ai_summary": ai_summary,
            "ai_importance": ai_importance,
            "notified": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        reports.append(report)
        self._save(REPORTS_FILE, reports)
        return report

    def get_reports(self, watch_id: str | None = None, limit: int = 100) -> list:
        reports = self._load(REPORTS_FILE)
        if watch_id:
            reports = [r for r in reports if r["watch_id"] == watch_id]
        return sorted(reports, key=lambda x: x["created_at"], reverse=True)[:limit]

    def delete_user_data(self, user_email: str) -> dict:
        """Delete all data for a user (GDPR Art. 17 right to erasure)."""
        # Delete user's watches
        watches = self._load(WATCHES_FILE)
        user_watches = [w for w in watches if w.get("user_email") == user_email]
        watch_ids = {w["id"] for w in user_watches}
        remaining_watches = [w for w in watches if w.get("user_email") != user_email]
        self._save(WATCHES_FILE, remaining_watches)

        # Delete reports linked to user's watches
        reports = self._load(REPORTS_FILE)
        remaining_reports = [r for r in reports if r.get("watch_id") not in watch_ids]
        deleted_reports = len(reports) - len(remaining_reports)
        self._save(REPORTS_FILE, remaining_reports)

        return {
            "watches_deleted": len(user_watches),
            "reports_deleted": deleted_reports,
        }

    def mark_report_notified(self, report_id: str) -> bool:
        reports = self._load(REPORTS_FILE)
        for i, r in enumerate(reports):
            if r["id"] == report_id:
                r["notified"] = True
                reports[i] = r
                self._save(REPORTS_FILE, reports)
                return True
        return False


# Global instance
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
