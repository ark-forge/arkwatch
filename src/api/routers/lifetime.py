"""Lifetime free beta - 50 spots, email + URL collection, counter tracking."""

import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
URL_REGEX = re.compile(r"^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)+(/[^\s]*)?$")
DATA_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/lifetime_spots.json")
MAX_SPOTS = 50

# Rate limit: 3 submissions per IP per hour
_submit_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 3


def _load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_entries(entries: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DATA_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DATA_FILE))


class LifetimeClaimRequest(BaseModel):
    email: str
    url: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        # Auto-add https:// if missing scheme
        if not v.startswith("http://") and not v.startswith("https://"):
            v = "https://" + v
        if not URL_REGEX.match(v) or len(v) > 2048:
            raise ValueError("Invalid URL")
        return v


@router.get("/api/v1/lifetime/spots")
async def get_remaining_spots():
    """Get number of remaining lifetime free spots."""
    entries = _load_entries()
    remaining = max(0, MAX_SPOTS - len(entries))
    return {"total": MAX_SPOTS, "claimed": len(entries), "remaining": remaining}


@router.post("/api/v1/lifetime/claim")
async def claim_lifetime_spot(req: LifetimeClaimRequest, request: Request):
    """Claim a free lifetime spot. Stores email + URL to monitor."""
    # Rate limit
    client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    now = time.time()
    _submit_attempts[client_ip] = [t for t in _submit_attempts[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_submit_attempts[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")
    _submit_attempts[client_ip].append(now)

    entries = _load_entries()

    # Check duplicate email
    if any(e["email"] == req.email for e in entries):
        remaining = max(0, MAX_SPOTS - len(entries))
        return {
            "status": "already_claimed",
            "message": "You've already claimed your spot! We'll send setup instructions soon.",
            "remaining": remaining,
        }

    # Check capacity
    if len(entries) >= MAX_SPOTS:
        raise HTTPException(status_code=410, detail="Sorry, all 50 lifetime spots have been claimed.")

    entries.append({
        "email": req.email,
        "url": req.url,
        "claimed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": client_ip,
        "source": request.headers.get("referer", "direct"),
    })
    _save_entries(entries)

    remaining = max(0, MAX_SPOTS - len(entries))
    spot_number = len(entries)

    return {
        "status": "ok",
        "message": f"You're #{spot_number}! Your free lifetime spot is secured.",
        "remaining": remaining,
        "spot_number": spot_number,
    }
