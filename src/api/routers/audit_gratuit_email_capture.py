#!/usr/bin/env python3
"""
API endpoint pour capturer emails depuis exit-intent popup sur /audit-gratuit-monitoring.html
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr
import json
from datetime import datetime, timezone
from pathlib import Path

router = APIRouter()

# Data files
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
CAPTURES_FILE = DATA_DIR / "audit_gratuit_email_captures.json"
VISITOR_LOG = DATA_DIR / "audit_gratuit_visitors.jsonl"


class EmailCapture(BaseModel):
    email: EmailStr
    visitor_id: str
    ip: str | None = None
    time_on_page: int = 0
    scroll_depth: int = 0
    form_started: bool = False
    form_submitted: bool = False
    referrer: str | None = None
    user_agent: str | None = None


def load_captures():
    """Load existing captures."""
    if not CAPTURES_FILE.exists():
        return {"captures": [], "stats": {"total": 0}}

    try:
        with open(CAPTURES_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {"captures": [], "stats": {"total": 0}}


def save_captures(data):
    """Save captures atomically."""
    CAPTURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = CAPTURES_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(CAPTURES_FILE)


@router.post("/audit-gratuit/capture-email")
async def capture_email(capture: EmailCapture, request: Request):
    """
    Capture email from exit-intent popup on audit-gratuit page.

    Called when visitor triggers exit-intent and submits email in popup.
    Links the anonymous visitor_id to an email address for conversion sequence.
    """
    # Get IP from request
    ip = capture.ip or request.client.host

    # Load existing captures
    data = load_captures()

    # Check if already captured (prevent duplicates)
    existing = next(
        (c for c in data["captures"] if c.get("email", "").lower() == capture.email.lower()),
        None
    )

    if existing:
        # Update existing capture with new data
        existing["last_seen"] = datetime.now(timezone.utc).isoformat()
        existing["time_on_page"] = max(existing.get("time_on_page", 0), capture.time_on_page)
        existing["scroll_depth"] = max(existing.get("scroll_depth", 0), capture.scroll_depth)
        existing["form_started"] = existing.get("form_started", False) or capture.form_started
        existing["form_submitted"] = existing.get("form_submitted", False) or capture.form_submitted
    else:
        # New capture
        data["captures"].append({
            "email": capture.email.lower(),
            "visitor_id": capture.visitor_id,
            "ip": ip,
            "time_on_page": capture.time_on_page,
            "scroll_depth": capture.scroll_depth,
            "form_started": capture.form_started,
            "form_submitted": capture.form_submitted,
            "referrer": capture.referrer,
            "user_agent": capture.user_agent or request.headers.get("user-agent"),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        })
        data["stats"]["total"] += 1

    save_captures(data)

    return {
        "status": "ok",
        "message": "Email captured successfully",
        "enrolled": not existing,
        "total_captures": data["stats"]["total"],
    }


@router.get("/audit-gratuit/capture-stats")
async def get_capture_stats():
    """Get email capture statistics."""
    data = load_captures()

    # Count by time_on_page buckets
    buckets = {"<60s": 0, "60-120s": 0, ">120s": 0}
    for c in data["captures"]:
        time = c.get("time_on_page", 0)
        if time < 60:
            buckets["<60s"] += 1
        elif time < 120:
            buckets["60-120s"] += 1
        else:
            buckets[">120s"] += 1

    # Count conversions
    conversions = sum(1 for c in data["captures"] if c.get("form_submitted", False))

    return {
        "total_captures": data["stats"]["total"],
        "time_buckets": buckets,
        "conversions": conversions,
        "conversion_rate": round(conversions / max(data["stats"]["total"], 1) * 100, 2),
    }
