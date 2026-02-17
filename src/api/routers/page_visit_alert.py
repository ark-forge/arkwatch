"""Page visit alert endpoint for tracking high-value page visits"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

# Simple JSONL log file (append-only, no locking issues)
# Use workspace/arkwatch/data which is accessible by the API service
LOG_PATH = "/opt/claude-ceo/workspace/arkwatch/data/page_visits.jsonl"


class PageVisitEvent(BaseModel):
    page: str  # /try, /demo, /pricing
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None


@router.post("/api/page-visit-alert")
async def track_page_visit(event: PageVisitEvent, request: Request):
    """
    Track visits to high-value pages (/try, /demo, /pricing).
    Logs IP, user-agent, timestamp for lead generation follow-up.
    """
    # Extract visitor info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Build log entry
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build log entry
    log_entry = {
        "timestamp": timestamp,
        "page": event.page,
        "ip": client_ip,
        "user_agent": user_agent,
        "referrer": event.referrer,
        "utm_source": event.utm_source,
        "utm_campaign": event.utm_campaign,
        "processed": False
    }

    # Append to JSONL log (simple, reliable)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Warning: Could not write visit log: {e}")

    return {
        "status": "logged",
        "page": event.page,
        "timestamp": timestamp,
    }


@router.get("/api/page-visit-alert/health")
async def page_visit_health():
    """Health check for page visit tracking"""
    visit_count = 0
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r") as f:
                visit_count = sum(1 for _ in f)
        except Exception:
            pass

    return {
        "status": "healthy",
        "log_path": LOG_PATH,
        "log_exists": os.path.exists(LOG_PATH),
        "total_visits": visit_count,
    }
