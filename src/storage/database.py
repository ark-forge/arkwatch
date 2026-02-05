"""Database connection and operations"""
import os
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import json

# For MVP, we use a simple JSON file storage
# Will be replaced by PostgreSQL for production

DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
WATCHES_FILE = f"{DATA_DIR}/watches.json"
REPORTS_FILE = f"{DATA_DIR}/reports.json"


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
    
    def _load(self, filepath: str) -> list:
        with open(filepath, "r") as f:
            return json.load(f)
    
    def _save(self, filepath: str, data: list):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    # Watches
    def create_watch(self, name: str, url: str, check_interval: int = 3600, 
                     notify_email: Optional[str] = None) -> dict:
        watches = self._load(WATCHES_FILE)
        watch = {
            "id": str(uuid4()),
            "name": name,
            "url": url,
            "check_interval": check_interval,
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
    
    def get_watches(self, status: Optional[str] = None) -> list:
        watches = self._load(WATCHES_FILE)
        if status:
            return [w for w in watches if w["status"] == status]
        return watches
    
    def get_watch(self, watch_id: str) -> Optional[dict]:
        watches = self._load(WATCHES_FILE)
        for w in watches:
            if w["id"] == watch_id:
                return w
        return None
    
    def update_watch(self, watch_id: str, **kwargs) -> Optional[dict]:
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
    def create_report(self, watch_id: str, changes_detected: bool, 
                      current_hash: str, previous_hash: Optional[str] = None,
                      diff: Optional[str] = None, ai_summary: Optional[str] = None,
                      ai_importance: Optional[str] = None) -> dict:
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
    
    def get_reports(self, watch_id: Optional[str] = None, limit: int = 100) -> list:
        reports = self._load(REPORTS_FILE)
        if watch_id:
            reports = [r for r in reports if r["watch_id"] == watch_id]
        return sorted(reports, key=lambda x: x["created_at"], reverse=True)[:limit]
    
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
_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
