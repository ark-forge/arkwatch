"""
Unified Email Tracking Router - Consolidates all email tracking into one endpoint.
Task: 20261105

Endpoints:
- GET /track/open/{lead_id} - Track email open via 1x1 pixel
- GET /track/click/{lead_id}/{redirect_url} - Track click and redirect
- GET /api/tracking/stats - Get consolidated tracking stats
"""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

router = APIRouter()

UNIFIED_TRACKING_FILE = "/opt/claude-ceo/workspace/arkwatch/data/unified_email_tracking.json"

# 1x1 transparent PNG pixel
TRACKING_PIXEL = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
    b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


def _load_tracking():
    path = Path(UNIFIED_TRACKING_FILE)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"metadata": {}, "leads": [], "hot_leads_top10": []}


def _save_tracking(data):
    path = Path(UNIFIED_TRACKING_FILE)
    data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def _find_lead_by_id(data, lead_id: str):
    for lead in data.get("leads", []):
        if lead.get("lead_id") == lead_id:
            return lead
    return None


def _find_lead_by_email(data, email: str):
    for lead in data.get("leads", []):
        if lead.get("lead_email") == email:
            return lead
    return None


def _recalculate_heat_score(lead: dict) -> int:
    score = 0
    opens = lead.get("opens_count", 0)
    clicks = lead.get("clicks_count", 0)

    if opens >= 1:
        score += 40
    if opens >= 2:
        score += 15 * (opens - 1)

    score += clicks * 30

    if lead.get("replied"):
        score += 50
    if lead.get("trial_activated"):
        score += 80

    emails_no_open = lead.get("emails_received", 1)
    if opens == 0 and emails_no_open > 1:
        score -= 5 * (emails_no_open - 1)

    # Recency bonus
    last_activity = lead.get("last_activity")
    if last_activity:
        try:
            last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            now = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.utcnow()
            hours_ago = (now - last_dt.replace(tzinfo=None)).total_seconds() / 3600
            if hours_ago < 6:
                score += 10
            elif hours_ago < 24:
                score += 5
        except (ValueError, TypeError):
            pass

    return max(0, min(100, score))


@router.get("/track/open/{lead_id}")
async def track_open(lead_id: str, request: Request):
    """Track email open via 1x1 transparent pixel."""
    now = datetime.utcnow().isoformat() + "Z"

    data = _load_tracking()
    lead = _find_lead_by_id(data, lead_id)

    if lead:
        lead["opens_count"] = lead.get("opens_count", 0) + 1
        if not lead.get("first_open_at"):
            lead["first_open_at"] = now
        lead["last_activity"] = now
        if "open_timestamps" not in lead:
            lead["open_timestamps"] = []
        lead["open_timestamps"].append(now)
        lead["heat_score"] = _recalculate_heat_score(lead)
        _save_tracking(data)

    return Response(
        content=TRACKING_PIXEL,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/track/click/{lead_id}/{url:path}")
async def track_click(lead_id: str, url: str, request: Request):
    """Track email click and redirect to target URL."""
    now = datetime.utcnow().isoformat() + "Z"
    redirect_url = unquote(url)

    if not redirect_url.startswith("http"):
        redirect_url = "https://" + redirect_url

    data = _load_tracking()
    lead = _find_lead_by_id(data, lead_id)

    if lead:
        lead["clicks_count"] = lead.get("clicks_count", 0) + 1
        lead["last_activity"] = now
        lead["heat_score"] = _recalculate_heat_score(lead)
        _save_tracking(data)

    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/api/tracking/stats")
async def get_tracking_stats():
    """Return consolidated tracking statistics."""
    data = _load_tracking()
    leads = data.get("leads", [])

    total = len(leads)
    with_opens = sum(1 for l in leads if l.get("opens_count", 0) > 0)
    total_opens = sum(l.get("opens_count", 0) for l in leads)
    total_clicks = sum(l.get("clicks_count", 0) for l in leads)

    hot_leads = [l for l in leads if l.get("heat_score", 0) >= 50]

    return {
        "total_leads_tracked": total,
        "leads_with_opens": with_opens,
        "open_rate_pct": round(with_opens / total * 100, 1) if total > 0 else 0,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "hot_leads_count": len(hot_leads),
        "hot_leads": [
            {
                "lead_id": l["lead_id"],
                "name": l.get("lead_name"),
                "company": l.get("company"),
                "heat_score": l.get("heat_score", 0),
                "opens": l.get("opens_count", 0),
                "clicks": l.get("clicks_count", 0),
            }
            for l in sorted(hot_leads, key=lambda x: x.get("heat_score", 0), reverse=True)
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
