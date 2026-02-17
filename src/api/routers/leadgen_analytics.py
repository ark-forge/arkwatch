"""Lead generation analytics tracking for conversion optimization."""

import json
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()

# Data file for analytics events
ANALYTICS_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/leadgen_analytics.json")
DEMO_LEADS_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/demo_leads.json")

# Rate limit: 100 events per IP per hour
_event_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 100


def _load_analytics() -> list[dict]:
    """Load analytics events from file."""
    if not ANALYTICS_FILE.exists():
        return []
    try:
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_analytics(events: list[dict]):
    """Save analytics events to file."""
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(ANALYTICS_FILE) + ".tmp"

    # Keep only last 10,000 events to prevent file bloat
    if len(events) > 10000:
        events = events[-10000:]

    with open(tmp, "w") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(ANALYTICS_FILE))


def _aggregate_analytics() -> dict:
    """Aggregate analytics for conversion funnel analysis."""
    events = _load_analytics()

    # Group by session (IP + date)
    sessions = defaultdict(lambda: {
        "events": [],
        "first_seen": None,
        "last_seen": None,
        "source": "direct",
        "page": "unknown",
    })

    for event in events:
        session_id = f"{event['ip']}_{event['date'][:10]}"  # IP + date (YYYY-MM-DD)
        sessions[session_id]["events"].append(event["event"])

        if not sessions[session_id]["first_seen"]:
            sessions[session_id]["first_seen"] = event["timestamp"]
        sessions[session_id]["last_seen"] = event["timestamp"]
        sessions[session_id]["source"] = event.get("source", "direct")
        sessions[session_id]["page"] = event.get("page", "unknown")

    # Calculate conversion metrics
    stats = {
        "total_sessions": len(sessions),
        "pageviews": 0,
        "exit_popup_shown": 0,
        "exit_popup_closed": 0,
        "exit_popup_cta_clicked": 0,
        "exit_popup_calendly_clicked": 0,
        "signup_attempts": 0,
        "signup_success": 0,
        "signup_failed": 0,
        "signup_error": 0,
        "scroll_25": 0,
        "scroll_50": 0,
        "scroll_75": 0,
        "scroll_100": 0,
        "time_on_page_10s": 0,
        "time_on_page_30s": 0,
        "time_on_page_60s": 0,
        "time_on_page_120s": 0,
        "time_on_page_300s": 0,
        "sources": defaultdict(int),
        "pages": defaultdict(int),
    }

    for session_data in sessions.values():
        event_list = session_data["events"]
        stats["sources"][session_data["source"]] += 1
        stats["pages"][session_data["page"]] += 1

        if "pageview_free_trial_leadgen" in event_list:
            stats["pageviews"] += 1
        if "exit_popup_shown" in event_list:
            stats["exit_popup_shown"] += 1
        if "exit_popup_closed" in event_list:
            stats["exit_popup_closed"] += 1
        if "exit_popup_cta_clicked" in event_list:
            stats["exit_popup_cta_clicked"] += 1
        if "exit_popup_calendly_clicked" in event_list:
            stats["exit_popup_calendly_clicked"] += 1
        if any("submit_free_trial" in e for e in event_list):
            stats["signup_attempts"] += 1
        if "signup_success" in event_list:
            stats["signup_success"] += 1
        if "signup_failed" in event_list:
            stats["signup_failed"] += 1
        if "signup_error" in event_list:
            stats["signup_error"] += 1
        if "scroll_25" in event_list:
            stats["scroll_25"] += 1
        if "scroll_50" in event_list:
            stats["scroll_50"] += 1
        if "scroll_75" in event_list:
            stats["scroll_75"] += 1
        if "scroll_100" in event_list:
            stats["scroll_100"] += 1
        if "time_on_page_10s" in event_list:
            stats["time_on_page_10s"] += 1
        if "time_on_page_30s" in event_list:
            stats["time_on_page_30s"] += 1
        if "time_on_page_60s" in event_list:
            stats["time_on_page_60s"] += 1
        if "time_on_page_120s" in event_list:
            stats["time_on_page_120s"] += 1
        if "time_on_page_300s" in event_list:
            stats["time_on_page_300s"] += 1

    # Calculate conversion rates
    if stats["pageviews"] > 0:
        stats["exit_popup_rate"] = round(stats["exit_popup_shown"] / stats["pageviews"] * 100, 2)
        stats["exit_popup_conversion_rate"] = round(
            stats["exit_popup_cta_clicked"] / max(stats["exit_popup_shown"], 1) * 100, 2
        )
        stats["calendly_rate"] = round(
            stats["exit_popup_calendly_clicked"] / max(stats["exit_popup_shown"], 1) * 100, 2
        )
        stats["signup_rate"] = round(stats["signup_attempts"] / stats["pageviews"] * 100, 2)
        stats["signup_success_rate"] = round(
            stats["signup_success"] / max(stats["signup_attempts"], 1) * 100, 2
        )
        stats["scroll_engagement_50"] = round(stats["scroll_50"] / stats["pageviews"] * 100, 2)
        stats["scroll_engagement_100"] = round(stats["scroll_100"] / stats["pageviews"] * 100, 2)
        stats["engaged_users_30s"] = round(stats["time_on_page_30s"] / stats["pageviews"] * 100, 2)

    # Convert defaultdicts to regular dicts
    stats["sources"] = dict(stats["sources"])
    stats["pages"] = dict(stats["pages"])

    return stats


@router.get("/t.gif")
async def track_event(e: str, p: str = "unknown", s: str = "direct", request: Request = None):
    """
    Track analytics event via 1x1 transparent GIF pixel.

    Parameters:
    - e: event name
    - p: page name
    - s: traffic source
    """
    # Rate limit check
    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )
    now = time.time()
    _event_attempts[client_ip] = [
        t for t in _event_attempts[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    # Allow tracking but rate limit to prevent abuse
    if len(_event_attempts[client_ip]) < RATE_LIMIT_MAX:
        _event_attempts[client_ip].append(now)

        # Load existing events
        events = _load_analytics()

        # Add new event
        events.append({
            "event": e,
            "page": p,
            "source": s,
            "ip": client_ip,
            "timestamp": now,
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
        })

        # Save events
        _save_analytics(events)

    # Return 1x1 transparent GIF
    gif_data = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
        b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00'
        b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
        b'\x44\x01\x00\x3b'
    )

    return Response(
        content=gif_data,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@router.get("/api/leadgen/analytics")
async def get_analytics():
    """Get aggregated analytics for conversion funnel."""
    stats = _aggregate_analytics()
    return {
        "success": True,
        "stats": stats,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.get("/api/leadgen/analytics/raw")
async def get_raw_analytics(limit: int = 100):
    """Get raw analytics events (last N events)."""
    events = _load_analytics()

    # Return last N events
    return {
        "success": True,
        "total": len(events),
        "events": events[-limit:] if limit > 0 else events,
    }


class DemoLeadRequest(BaseModel):
    """Request model for demo lead capture."""
    email: str
    source: str = "demo_page"
    timestamp: str


@router.post("/api/demo-leads")
async def capture_demo_lead(lead: DemoLeadRequest, request: Request):
    """
    Capture email from demo page for lead generation.

    This endpoint stores qualified leads who unlock the full demo.
    Target: 10% conversion rate from HN visitors.
    """
    # Get client IP for deduplication
    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )

    # Load existing demo leads
    demo_leads = []
    if DEMO_LEADS_FILE.exists():
        try:
            with open(DEMO_LEADS_FILE) as f:
                demo_leads = json.load(f)
        except (json.JSONDecodeError, OSError):
            demo_leads = []

    # Check if email already exists (prevent duplicates)
    existing_emails = {lead.get("email") for lead in demo_leads}
    is_new = lead.email not in existing_emails

    # Add new lead
    lead_data = {
        "email": lead.email,
        "source": lead.source,
        "timestamp": lead.timestamp,
        "ip": client_ip,
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "is_new": is_new,
    }

    demo_leads.append(lead_data)

    # Save to file
    DEMO_LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DEMO_LEADS_FILE) + ".tmp"

    # Keep last 5,000 leads to prevent file bloat
    if len(demo_leads) > 5000:
        demo_leads = demo_leads[-5000:]

    with open(tmp, "w") as f:
        json.dump(demo_leads, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DEMO_LEADS_FILE))

    # Track event in analytics
    events = _load_analytics()
    events.append({
        "event": "demo_lead_captured",
        "page": "demo",
        "source": lead.source,
        "ip": client_ip,
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
        "email_hash": hash(lead.email),  # Don't store plain email in analytics
    })
    _save_analytics(events)

    return {
        "success": True,
        "message": "Lead captured successfully",
        "is_new": is_new,
        "redirect_to": "/site/trial-14d.html?from=demo",
    }


@router.get("/api/demo-leads/stats")
async def get_demo_leads_stats():
    """Get statistics about demo leads conversion."""
    if not DEMO_LEADS_FILE.exists():
        return {
            "success": True,
            "total_leads": 0,
            "unique_leads": 0,
            "sources": {},
            "leads": [],
        }

    try:
        with open(DEMO_LEADS_FILE) as f:
            demo_leads = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "success": True,
            "total_leads": 0,
            "unique_leads": 0,
            "sources": {},
            "leads": [],
        }

    # Count unique emails
    unique_emails = set()
    sources = defaultdict(int)

    for lead in demo_leads:
        unique_emails.add(lead.get("email", ""))
        sources[lead.get("source", "unknown")] += 1

    return {
        "success": True,
        "total_leads": len(demo_leads),
        "unique_leads": len(unique_emails),
        "sources": dict(sources),
        "recent_leads": demo_leads[-20:],  # Last 20 leads
    }
