"""API endpoint pour tracking visiteurs /trial-14d en temps réel"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

# Paths
VISITOR_LOG = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_visitors.jsonl"


class VisitorEvent(BaseModel):
    """Event de tracking visiteur"""
    visitor_id: str
    type: str  # click, scroll, form_focus, form_input, form_submit, heartbeat, page_leave
    timestamp: str
    page: str
    interactions: Optional[int] = None
    depth: Optional[int] = None
    time_on_page: Optional[int] = None
    scrollDepth: Optional[int] = None
    field: Optional[str] = None


@router.post("/api/track-visitor-trial14d")
async def track_visitor_trial14d(event: VisitorEvent, request: Request):
    """
    Endpoint de tracking temps réel pour visiteurs /trial-14d.

    Capture:
    - Clicks, scrolls, interactions formulaire
    - Temps passé sur page
    - Profondeur de scroll
    - Abandon de formulaire

    Les données sont analysées en temps réel par hot_visitor_tracker_trial14d.py
    pour détecter les visiteurs HOT et envoyer alertes SMS.
    """
    # Enrich event with request data
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

    # Add optional fields
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

    # Log event to JSONL file
    Path(VISITOR_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(VISITOR_LOG, "a") as f:
        f.write(json.dumps(event_data) + "\n")

    return {
        "status": "tracked",
        "visitor_id": event.visitor_id,
        "event_type": event.type,
    }


@router.get("/api/track-visitor-trial14d/stats")
async def get_visitor_stats():
    """Get visitor tracking statistics"""
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
                events.append(json.loads(line))

        # Count unique visitors
        unique_visitors = len(set(e.get("visitor_id", "") for e in events))

        # Count events by type
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
