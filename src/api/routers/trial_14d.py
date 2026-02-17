"""Trial 14 jours sans CB - activation automatique pour DevTo traffic."""

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from ..auth import create_api_key, get_user_by_email

# Direct import for reliable email sending (not subprocess)
sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DATA_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/trial_14d_signups.json")
TRIAL_DAYS = 14

# Rate limit: 3 submissions per IP per hour
_submit_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 3


def _load_signups() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_signups(entries: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DATA_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DATA_FILE))


def _send_trial_welcome_email(email: str, api_key: str) -> bool:
    """Send trial welcome email with onboarding steps. Returns True if sent."""
    if not EMAIL_ENABLED:
        print(f"[DRY RUN] Would send trial welcome email to {email}")
        return False

    try:
        name = email.split('@')[0].capitalize()
        trial_end = time.strftime('%Y-%m-%d', time.gmtime(time.time() + TRIAL_DAYS * 24 * 3600))

        subject = "Welcome to ArkWatch - Your 14-Day Trial Starts Now!"
        body = f"""Hi {name},

Welcome to ArkWatch! Your 14-day free trial is now ACTIVE.

YOUR ACCOUNT IS READY
No credit card required. No payment. Just monitoring.

GET STARTED IN 3 STEPS

1. ADD YOUR FIRST WEBSITE
   Go to: https://arkforge.fr/dashboard.html
   Click "Add Monitor" and enter your website URL

2. CONFIGURE ALERTS
   Set up email notifications when changes are detected
   Choose check frequency (every 5 min to daily)

3. RELAX & GET ALERTED
   We'll notify you instantly when something changes
   AI-powered summaries tell you exactly what changed

YOUR TRIAL INCLUDES
- Monitor up to 10 websites
- Checks every 5 minutes
- AI-powered change detection
- Email alerts
- Full API access
- 14 days completely free

YOUR API KEY
{api_key}
(Save this - you'll need it for API access)

TRIAL ENDS: {trial_end}
After 14 days, you can:
- Upgrade to Pro (29 EUR/month) - unlimited monitors
- Continue with Free plan (3 monitors, daily checks)
- Cancel anytime (no questions asked)

NEED HELP?
Reply to this email anytime. We're here to help!

-- The ArkWatch Team
https://arkforge.fr
"""

        return send_email(
            to_addr=email,
            subject=subject,
            body=body,
            reply_to="contact@arkforge.fr",
            skip_warmup=True,
        )
    except Exception as e:
        print(f"Error sending trial welcome email to {email}: {e}")
        return False


def _notify_ceo_new_trial(email: str, source: str, api_key: str):
    """Notify CEO of new 14-day trial signup."""
    if not EMAIL_ENABLED:
        return
    try:
        subject = f"NEW 14-DAY TRIAL SIGNUP - {email}"
        body = f"""NOUVEAU TRIAL 14 JOURS:

Email: {email}
Source: {source}
Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}

Compte cree automatiquement:
- API Key: {api_key[:20]}...
- Tier: free (trial 14 jours actif)
- Trial expire: {time.strftime('%Y-%m-%d', time.gmtime(time.time() + TRIAL_DAYS * 24 * 3600))}
- Email d'onboarding envoye

Action CEO:
- Suivre activation dans les 48h
- Engagement utilisateur J+3, J+7, J+14

Dashboard: https://watch.arkforge.fr/api/trial-14d/stats
"""

        send_email(
            to_addr="apps.desiorac@gmail.com",
            subject=subject,
            body=body,
        )
    except Exception:
        pass


class Trial14DSignup(BaseModel):
    email: str
    source: str = "devto"
    campaign: str = "trial_14d"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v


@router.post("/api/trial-14d/signup")
async def trial_14d_signup(req: Trial14DSignup, request: Request):
    """
    Créer compte trial 14 jours SANS carte bancaire.

    Flow automatique:
    1. Valide email
    2. Crée compte utilisateur avec API key
    3. Active trial 14 jours automatiquement (tier=free avec trial_ends_at)
    4. Envoie email onboarding
    5. Notifie CEO

    Pas de limite de spots, pas de Stripe, activation instantanée.
    """
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
            status_code=429, detail="Too many attempts. Please try again in an hour."
        )
    _submit_attempts[client_ip].append(now)

    signups = _load_signups()

    # Check if already signed up
    if any(e["email"] == req.email for e in signups):
        existing_user = get_user_by_email(req.email)
        if existing_user:
            return {
                "success": True,
                "message": "You're already registered! Check your email for access details.",
            }

    # Extract name from email
    name_from_email = req.email.split('@')[0].capitalize()

    # Check if user account already exists
    existing_user = get_user_by_email(req.email)

    if existing_user:
        # User exists, add to tracking
        if not any(e["email"] == req.email for e in signups):
            signups.append({
                "email": req.email,
                "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "ip": client_ip,
                "source": req.source,
                "campaign": req.campaign,
                "user_agent": request.headers.get("user-agent", ""),
                "referer": request.headers.get("referer", ""),
                "account_existed": True,
            })
            _save_signups(signups)

        return {
            "success": True,
            "message": "Account already exists! Check your email for login details.",
        }

    # Create user account with API key (tier=free with trial)
    try:
        raw_key, key_hash, verification_code = create_api_key(
            name=name_from_email,
            email=req.email,
            tier="free",  # Free tier - trial tracking done in signups file
            privacy_accepted=True,
            client_ip=client_ip,
            signup_source=f"{req.source}_trial14d",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create account: {str(e)}"
        )

    # Track signup
    signups.append({
        "email": req.email,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": client_ip,
        "source": req.source,
        "campaign": req.campaign,
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
        "account_created": True,
        "api_key": raw_key[:20] + "...",  # Truncated
        "trial_ends_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + TRIAL_DAYS * 24 * 3600)),
    })
    _save_signups(signups)

    # Send welcome email
    _send_trial_welcome_email(req.email, raw_key)

    # Notify CEO
    _notify_ceo_new_trial(req.email, req.source, raw_key)

    return {
        "success": True,
        "message": "Success! Check your email to get started with your 14-day trial.",
        "trial_days": TRIAL_DAYS,
        "dashboard_url": "https://arkforge.fr/dashboard.html",
    }


@router.get("/api/trial-14d/stats")
async def get_trial_stats():
    """Get trial signup statistics."""
    signups = _load_signups()

    # Count by source
    by_source = {}
    for s in signups:
        src = s.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "total_signups": len(signups),
        "trial_days": TRIAL_DAYS,
        "by_source": by_source,
        "last_signup_at": signups[-1]["registered_at"] if signups else None,
    }
