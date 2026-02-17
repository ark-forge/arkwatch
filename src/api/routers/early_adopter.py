"""Early-adopter email collection - minimal endpoint, JSON storage, no external deps."""

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
DATA_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/early_adopters.json")

# Rate limit: 3 submissions per IP per hour
_submit_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 3


def _load_emails() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_emails(entries: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DATA_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DATA_FILE))


class EarlyAdopterRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v


@router.post("/api/v1/early-adopter")
async def collect_early_adopter_email(req: EarlyAdopterRequest, request: Request):
    """Collect an email for the early-adopter waitlist. No account created, just stores the email."""
    # Rate limit
    client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    now = time.time()
    _submit_attempts[client_ip] = [t for t in _submit_attempts[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_submit_attempts[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez plus tard.")
    _submit_attempts[client_ip].append(now)

    entries = _load_emails()

    # Check duplicate
    if any(e["email"] == req.email for e in entries):
        return {"status": "already_registered", "message": "Cet email est déjà inscrit. Vous serez notifié(e) !"}

    entries.append({
        "email": req.email,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": client_ip,
        "source": request.headers.get("referer", "direct"),
    })
    _save_emails(entries)

    return {"status": "ok", "message": "Merci ! Vous serez notifié(e) dès le lancement de l'offre early-adopter."}
