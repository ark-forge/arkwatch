"""API endpoint pour tracking visiteurs /audit-gratuit-monitoring.html en temps réel"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

VISITOR_LOG = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_visitors.jsonl"


class AuditVisitorEvent(BaseModel):
    """Event de tracking visiteur page audit gratuit"""
    visitor_id: str
    type: str  # pageview, click, scroll, form_focus, form_input, form_submit, heartbeat, page_leave
    timestamp: str
    page: str
    interactions: Optional[int] = None
    depth: Optional[int] = None
    time_on_page: Optional[int] = None
    scrollDepth: Optional[int] = None
    field: Optional[str] = None


@router.post("/api/track-visitor-audit-gratuit")
async def track_visitor_audit_gratuit(event: AuditVisitorEvent, request: Request):
    """
    Endpoint de tracking temps réel pour visiteurs /audit-gratuit-monitoring.html.

    Capture: clicks, scrolls, form interactions, temps passé, profondeur scroll.
    Données analysées par hot_visitor_tracker_audit_gratuit.py pour alertes SMS.
    """
    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )

    event_data = {
        "visitor_id": event.visitor_id,
        "type": event.type,
        "timestamp": event.timestamp,
        "page": event.page,
        "ip": client_ip,
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
    }

    if event.interactions is not None:
        event_data["interactions"] = event.interactions
    if event.depth is not None:
        event_data["depth"] = event.depth
    if event.time_on_page is not None:
        event_data["time_on_page"] = event.time_on_page
    if event.scrollDepth is not None:
        event_data["scroll_depth"] = event.scrollDepth
    if event.field:
        event_data["field"] = event.field

    Path(VISITOR_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(VISITOR_LOG, "a") as f:
        f.write(json.dumps(event_data) + "\n")

    return {
        "status": "tracked",
        "visitor_id": event.visitor_id,
        "event_type": event.type,
    }


@router.get("/api/track-visitor-audit-gratuit/stats")
async def get_audit_visitor_stats():
    """Get audit-gratuit visitor tracking statistics"""
    if not Path(VISITOR_LOG).exists():
        return {
            "total_events": 0,
            "unique_visitors": 0,
            "events_by_type": {},
        }

    try:
        events = []
        with open(VISITOR_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

        unique_visitors = len(set(e.get("visitor_id", "") for e in events))

        events_by_type = {}
        for e in events:
            event_type = e.get("type", "unknown")
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

        return {
            "total_events": len(events),
            "unique_visitors": unique_visitors,
            "events_by_type": events_by_type,
            "last_event": events[-1] if events else None,
        }

    except Exception as e:
        return {
            "error": str(e),
            "total_events": 0,
            "unique_visitors": 0,
        }
