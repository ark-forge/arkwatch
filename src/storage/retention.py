"""RGPD data retention enforcement (Art. 5.1.e - Storage limitation).

Purges expired data according to the documented retention periods:
- Reports: 12 months
- Nginx access logs: 12 months (handled by logrotate, not this script)
- Account data after deletion: immediate (handled by DELETE /account)

Run daily via cron or systemd timer.
"""

import json
import os
from datetime import UTC, datetime, timedelta

DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
REPORTS_FILE = f"{DATA_DIR}/reports.json"

# Retention period for reports (12 months)
REPORTS_RETENTION_DAYS = 365


def _load(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        return json.load(f)


def _save(filepath: str, data: list):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def purge_old_reports() -> int:
    """Remove reports older than REPORTS_RETENTION_DAYS. Returns count of deleted reports."""
    reports = _load(REPORTS_FILE)
    cutoff = (datetime.now(UTC) - timedelta(days=REPORTS_RETENTION_DAYS)).isoformat()

    remaining = [r for r in reports if r.get("created_at", "") > cutoff]
    deleted = len(reports) - len(remaining)

    if deleted > 0:
        _save(REPORTS_FILE, remaining)

    return deleted


def run_retention():
    """Execute all retention policies."""
    now = datetime.now(UTC).isoformat()
    deleted_reports = purge_old_reports()

    log_entry = f"[{now}] Retention: {deleted_reports} reports purged"
    print(log_entry)

    # Write to retention log
    log_file = f"{DATA_DIR}/retention.log"
    with open(log_file, "a") as f:
        f.write(log_entry + "\n")

    return {"reports_purged": deleted_reports}


if __name__ == "__main__":
    run_retention()
