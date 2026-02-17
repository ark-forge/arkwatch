"""Simple email subscription endpoint - stores emails in JSON, no external deps.
Each new subscriber triggers a webhook notification (logged + email to CEO)."""

import json
import logging
import os
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

logger = logging.getLogger("arkwatch.subscribe")

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DATA_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/subscribers.json")
NOTIFICATION_LOG = Path("/opt/claude-ceo/workspace/arkwatch/data/subscriber_notifications.log")
EMAIL_SENDER_PATH = "/opt/claude-ceo/automation/email_sender.py"
CEO_EMAIL = "contact@arkforge.fr"

# Rate limit: 3 submissions per IP per hour
_submit_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 3


def _load_subscribers() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_subscribers(entries: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DATA_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DATA_FILE))


class SubscribeRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v


@router.post("/api/subscribe")
async def subscribe_email(req: SubscribeRequest, request: Request):
    """Collect an email for downtime alerts notification list."""
    # Rate limit
    client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    now = time.time()
    _submit_attempts[client_ip] = [t for t in _submit_attempts[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_submit_attempts[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")
    _submit_attempts[client_ip].append(now)

    entries = _load_subscribers()

    # Check duplicate
    if any(e["email"] == req.email for e in entries):
        return {"status": "already_subscribed", "message": "You're already on the list! We'll notify you."}

    subscribed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    source = request.headers.get("referer", "direct")
    entries.append({
        "email": req.email,
        "subscribed_at": subscribed_at,
        "ip": client_ip,
        "source": source,
    })
    _save_subscribers(entries)

    # Webhook notification: log + email alert for new traction signal
    _notify_new_subscriber(req.email, subscribed_at, source, len(entries))

    return {"status": "ok", "message": "You're in! We'll email you when your site goes down."}


def _notify_new_subscriber(email: str, subscribed_at: str, source: str, total_count: int):
    """Fire-and-forget notification for each new subscriber (traction signal)."""
    # 1. Append to notification log (always succeeds)
    try:
        NOTIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(NOTIFICATION_LOG, "a") as f:
            f.write(json.dumps({
                "event": "new_subscriber",
                "email": email,
                "subscribed_at": subscribed_at,
                "source": source,
                "total_subscribers": total_count,
            }) + "\n")
    except OSError as e:
        logger.warning("Failed to write subscriber notification log: %s", e)

    # 2. Send email notification to internal CEO address (non-blocking, best-effort)
    try:
        subject = f"[ArkWatch] New subscriber #{total_count}: {email}"
        body = (
            f"New email subscriber on ArkWatch landing page.\n\n"
            f"Email: {email}\n"
            f"Source: {source}\n"
            f"Time: {subscribed_at}\n"
            f"Total subscribers: {total_count}\n\n"
            f"This is a real traction signal."
        )
        subprocess.Popen(
            ["python3", EMAIL_SENDER_PATH, CEO_EMAIL, subject, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning("Failed to send subscriber notification email: %s", e)
