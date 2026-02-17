"""Analytics and conversion statistics endpoints"""

import json
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user, is_admin

router = APIRouter()

API_KEYS_FILE = "/opt/claude-ceo/workspace/arkwatch/data/api_keys.json"


def _load_signups() -> list[dict]:
    """Load all signups with their metadata."""
    try:
        with open(API_KEYS_FILE) as f:
            keys = json.load(f)

        signups = []
        for key_hash, user_data in keys.items():
            signups.append({
                "email": user_data.get("email", "unknown"),
                "name": user_data.get("name", "unknown"),
                "source": user_data.get("signup_source", "direct"),
                "created_at": user_data.get("created_at"),
                "tier": user_data.get("tier", "free"),
                "email_verified": user_data.get("email_verified", False),
            })

        return signups
    except FileNotFoundError:
        return []


@router.get("/api/stats")
async def get_conversion_stats(user: dict = Depends(get_current_user)):
    """Get conversion statistics: signups by source and day.

    Admin-only endpoint. Returns:
    - Total signups count
    - Signups by source (aggregated)
    - Signups by day (last 30 days)
    - Signups by source per day
    """
    # Only admins can access stats
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")

    signups = _load_signups()

    if not signups:
        return {
            "total_signups": 0,
            "by_source": {},
            "by_day": {},
            "by_source_and_day": {},
        }

    # Aggregate by source
    by_source = defaultdict(int)
    by_day = defaultdict(int)
    by_source_and_day = defaultdict(lambda: defaultdict(int))

    for signup in signups:
        source = signup["source"]
        by_source[source] += 1

        # Extract day from created_at (ISO format: "2026-02-07T12:34:56.123456")
        created_at = signup.get("created_at")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                day = dt.strftime("%Y-%m-%d")
                by_day[day] += 1
                by_source_and_day[day][source] += 1
            except (ValueError, AttributeError):
                pass  # Skip invalid dates

    return {
        "total_signups": len(signups),
        "by_source": dict(by_source),
        "by_day": dict(sorted(by_day.items())),
        "by_source_and_day": {
            day: dict(sources)
            for day, sources in sorted(by_source_and_day.items())
        },
    }


@router.get("/api/stats/funnel")
async def get_funnel_stats(user: dict = Depends(get_current_user)):
    """Get funnel statistics: signup -> email verification -> paid conversion.

    Admin-only endpoint. Returns conversion rates at each funnel stage.
    """
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")

    signups = _load_signups()

    if not signups:
        return {
            "total_signups": 0,
            "email_verified": 0,
            "paid_conversions": 0,
            "verification_rate": 0.0,
            "paid_conversion_rate": 0.0,
        }

    total = len(signups)
    verified = sum(1 for s in signups if s.get("email_verified"))
    paid = sum(1 for s in signups if s.get("tier") not in ("free", None))

    verification_rate = (verified / total * 100) if total > 0 else 0.0
    paid_rate = (paid / total * 100) if total > 0 else 0.0

    return {
        "total_signups": total,
        "email_verified": verified,
        "paid_conversions": paid,
        "verification_rate": round(verification_rate, 2),
        "paid_conversion_rate": round(paid_rate, 2),
        "by_source": _get_funnel_by_source(signups),
    }


def _get_funnel_by_source(signups: list[dict]) -> dict:
    """Get funnel metrics broken down by source."""
    by_source = defaultdict(lambda: {"signups": 0, "verified": 0, "paid": 0})

    for signup in signups:
        source = signup["source"]
        by_source[source]["signups"] += 1

        if signup.get("email_verified"):
            by_source[source]["verified"] += 1

        if signup.get("tier") not in ("free", None):
            by_source[source]["paid"] += 1

    # Calculate rates
    result = {}
    for source, metrics in by_source.items():
        total = metrics["signups"]
        result[source] = {
            "signups": total,
            "verified": metrics["verified"],
            "paid": metrics["paid"],
            "verification_rate": round(metrics["verified"] / total * 100, 2) if total > 0 else 0.0,
            "paid_rate": round(metrics["paid"] / total * 100, 2) if total > 0 else 0.0,
        }

    return result
