"""First 3 Customers - Lifetime FREE in exchange for testimonial + case study."""

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
DATA_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/first_3_signups.json")
NOTIFICATION_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/first_3_notifications.log")
MAX_SPOTS = 3
OFFER_END_DATE = "2026-02-12T16:40:00Z"  # 72h from launch

# Rate limit: 5 submissions per IP per hour
_submit_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 5


def _load_signups() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_signups(signups: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DATA_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(signups, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DATA_FILE))


def _log_notification(signup_data: dict):
    """Log notification for Slack webhook (to be processed by worker)."""
    NOTIFICATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    notification = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "first_3_signup",
        "data": signup_data,
        "spot_number": signup_data.get("spot_number"),
    }
    with open(NOTIFICATION_FILE, "a") as f:
        f.write(json.dumps(notification, ensure_ascii=False) + "\n")


class First3SignupRequest(BaseModel):
    email: str
    company: str
    usecase: str
    linkedin: str = ""
    source: str = "direct"
    timestamp: str = ""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Please provide your company or role")
        if len(v) > 200:
            raise ValueError("Company name too long (max 200 chars)")
        return v

    @field_validator("usecase")
    @classmethod
    def validate_usecase(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Please describe your use case (minimum 10 characters)")
        if len(v) > 2000:
            raise ValueError("Use case too long (max 2000 chars)")
        return v

    @field_validator("linkedin")
    @classmethod
    def validate_linkedin(cls, v: str) -> str:
        v = v.strip()
        if v and not v.startswith("http"):
            raise ValueError("LinkedIn URL must start with http:// or https://")
        if len(v) > 500:
            raise ValueError("LinkedIn URL too long")
        return v


@router.get("/api/first-3/remaining")
async def get_remaining():
    """Get number of remaining First 3 spots."""
    signups = _load_signups()
    remaining = max(0, MAX_SPOTS - len(signups))
    return {
        "total": MAX_SPOTS,
        "claimed": len(signups),
        "remaining": remaining,
        "offer_ends": OFFER_END_DATE,
    }


@router.post("/api/first-3/signup")
async def signup(req: First3SignupRequest, request: Request):
    """Sign up for First 3 Customers lifetime free offer."""
    # Check if offer has ended
    current_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if current_time > OFFER_END_DATE:
        raise HTTPException(status_code=410, detail="Sorry, this offer has expired (72 hours elapsed).")

    # Rate limit
    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )
    now = time.time()
    _submit_attempts[client_ip] = [
        t for t in _submit_attempts[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_submit_attempts[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please slow down and try again in a few minutes.",
        )
    _submit_attempts[client_ip].append(now)

    signups = _load_signups()

    # Check duplicate email
    if any(e["email"] == req.email for e in signups):
        remaining = max(0, MAX_SPOTS - len(signups))
        return {
            "status": "already_claimed",
            "message": "You've already claimed your spot! Check your email for next steps.",
            "remaining": remaining,
        }

    # Check capacity
    if len(signups) >= MAX_SPOTS:
        raise HTTPException(
            status_code=410,
            detail="Sorry, all 3 spots have been claimed. You're too late!",
        )

    # Create signup entry
    signup_data = {
        "email": req.email,
        "company": req.company,
        "usecase": req.usecase,
        "linkedin": req.linkedin,
        "source": req.source,
        "claimed_at": current_time,
        "ip": client_ip,
        "referer": request.headers.get("referer", "direct"),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "spot_number": len(signups) + 1,
    }

    signups.append(signup_data)
    _save_signups(signups)

    # Log for Slack notification
    _log_notification(signup_data)

    remaining = max(0, MAX_SPOTS - len(signups))
    spot_number = signup_data["spot_number"]

    return {
        "status": "success",
        "message": f"CONGRATULATIONS! You're customer #{spot_number} of 3. Check your email for next steps.",
        "remaining": remaining,
        "spot_number": spot_number,
    }
