"""A/B Test routing for pricing page v1 vs v2 (FOMO/urgency variant)

50% traffic to pricing.html (v1), 50% to pricing-v2.html (v2).
Tracks pageviews and CTA clicks per version for conversion comparison.
"""

import json
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter(prefix="/api/pricing-ab", tags=["pricing-ab"])

# Data file for A/B test tracking (must be in ReadWritePaths for systemd)
AB_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "data",
    "pricing_ab_data.json",
)


def _load_data() -> dict:
    """Load A/B test tracking data."""
    if os.path.exists(AB_DATA_FILE):
        try:
            with open(AB_DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "start_date": datetime.now(timezone.utc).isoformat(),
        "v1": {"pageviews": 0, "cta_clicks": 0, "sources": {}},
        "v2": {"pageviews": 0, "cta_clicks": 0, "sources": {}},
        "events": [],
    }


def _save_data(data: dict) -> None:
    """Save A/B test tracking data."""
    os.makedirs(os.path.dirname(AB_DATA_FILE), exist_ok=True)
    with open(AB_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.get("/redirect")
async def ab_redirect(request: Request):
    """Redirect visitor to v1 or v2 based on 50/50 split.

    Uses a simple hash of the visitor's IP + user-agent for consistent assignment.
    Same visitor always gets the same version within a session.
    """
    # Deterministic assignment based on visitor fingerprint
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    fingerprint = hash(f"{client_ip}:{user_agent}") % 2

    version = "v1" if fingerprint == 0 else "v2"

    # Track the pageview
    data = _load_data()
    data[version]["pageviews"] += 1
    _save_data(data)

    if version == "v1":
        return RedirectResponse(url="/pricing.html?version=v1", status_code=302)
    else:
        return RedirectResponse(url="/pricing-v2.html?version=v2", status_code=302)


@router.post("/track")
async def track_event(request: Request):
    """Track A/B test events (pageview, cta_click)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    event = body.get("event", "unknown")
    version = body.get("version", "unknown")
    source = body.get("source", "direct")
    timestamp = body.get("timestamp", datetime.now(timezone.utc).isoformat())

    if version not in ("v1", "v2"):
        return JSONResponse({"error": "version must be v1 or v2"}, status_code=400)

    data = _load_data()

    if event == "cta_click":
        data[version]["cta_clicks"] += 1

    # Track source breakdown
    if source not in data[version]["sources"]:
        data[version]["sources"][source] = {"pageviews": 0, "cta_clicks": 0}
    if event == "pageview":
        data[version]["sources"][source]["pageviews"] += 1
    elif event == "cta_click":
        data[version]["sources"][source]["cta_clicks"] += 1

    # Keep last 200 events for debugging
    data["events"].append(
        {"event": event, "version": version, "source": source, "timestamp": timestamp}
    )
    data["events"] = data["events"][-200:]

    _save_data(data)

    return {"status": "ok", "tracked": event, "version": version}


@router.get("/stats")
async def get_stats():
    """Get current A/B test statistics and conversion rates."""
    data = _load_data()

    v1_views = data["v1"]["pageviews"]
    v1_clicks = data["v1"]["cta_clicks"]
    v2_views = data["v2"]["pageviews"]
    v2_clicks = data["v2"]["cta_clicks"]

    v1_rate = (v1_clicks / v1_views * 100) if v1_views > 0 else 0
    v2_rate = (v2_clicks / v2_views * 100) if v2_views > 0 else 0

    total_views = v1_views + v2_views
    winner = "inconclusive"
    if total_views >= 100:
        if v2_rate > v1_rate * 1.1:
            winner = "v2"
        elif v1_rate > v2_rate * 1.1:
            winner = "v1"
        else:
            winner = "tie"

    return {
        "status": "ok",
        "start_date": data.get("start_date", "unknown"),
        "total_views": total_views,
        "v1": {
            "pageviews": v1_views,
            "cta_clicks": v1_clicks,
            "conversion_rate": round(v1_rate, 2),
            "sources": data["v1"]["sources"],
        },
        "v2": {
            "pageviews": v2_views,
            "cta_clicks": v2_clicks,
            "conversion_rate": round(v2_rate, 2),
            "sources": data["v2"]["sources"],
        },
        "recommendation": winner,
        "sufficient_data": total_views >= 100,
    }
