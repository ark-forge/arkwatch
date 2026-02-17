"""
API endpoint - Track CTA clicks (Signal 2)
Records clicks on 'Réserver audit' button for conversion monitoring
"""

from fastapi import APIRouter, Request
from datetime import datetime, timezone
import json
from pathlib import Path

router = APIRouter()

CTA_CLICKS_LOG = "/opt/claude-ceo/workspace/arkwatch/data/cta_clicks.jsonl"


@router.post("/track_cta_click")
async def track_cta_click(request: Request):
    """
    Track CTA button clicks

    Expected payload:
    {
      "cta_id": "cta_reserver_audit",
      "visitor_id": "abc123",
      "page": "/audit-gratuit-monitoring.html"
    }
    """
    try:
        # Parse request
        data = await request.json()

        # Get client IP
        client_ip = request.client.host
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Build event
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cta_id": data.get("cta_id"),
            "visitor_id": data.get("visitor_id"),
            "page": data.get("page"),
            "ip": client_ip,
            "user_agent": request.headers.get("user-agent"),
            "referrer": request.headers.get("referer"),
        }

        # Append to log
        Path(CTA_CLICKS_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(CTA_CLICKS_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")

        return {
            "status": "ok",
            "tracked": True,
            "cta_id": event["cta_id"]
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
