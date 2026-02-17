"""Free trial 6 months - signup endpoint for ultra-conversion landing page."""

import json
import os
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from ...billing.stripe_service import StripeService
from ..auth import create_api_key, get_user_by_email

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DATA_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/free_trial_signups.json")
MAX_SPOTS = 10  # First 10 users get 6 months free

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


def _save_signups(entries: list[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(DATA_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(DATA_FILE))


def _notify_ceo_new_signup(email: str, source: str, spots_left: int, api_key: str = ""):
    """Notify CEO of new free trial signup via email."""
    try:
        subject = f"🎯 NEW FREE TRIAL SIGNUP - {spots_left}/{MAX_SPOTS} spots left"
        body = f"""NOUVELLE INSCRIPTION FREE TRIAL:

Email: {email}
Source: {source}
Places restantes: {spots_left}/{MAX_SPOTS}
Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}

Compte créé automatiquement:
- API Key: {api_key[:20]}... (tronqué pour sécurité)
- Tier: PRO (6 mois gratuits via Stripe promo 6MONTHSFREE)
- Email de bienvenue envoyé automatiquement

Action requise:
- Suivre l'activation du compte dans les 48h
- Vérifier création checkout session Stripe

Dashboard: https://watch.arkforge.fr/api/free-trial/spots
"""

        # Send email via email_sender.py
        subprocess.run(
            [
                "python3",
                "/opt/claude-ceo/automation/email_sender.py",
                "apps.desiorac@gmail.com",
                subject,
                body,
            ],
            timeout=10,
            check=False,
            capture_output=True,
        )
    except Exception:
        # Silent fail - don't break signup flow if notification fails
        pass


def _send_early_adopter_welcome_email(email: str, name: str, api_key: str, checkout_url: str):
    """Send special early adopter welcome email with 6 months free promo."""
    try:
        subject = f"🎉 Welcome {name}! You're Early Adopter #{len(_load_signups())}/10"
        body = f"""Hi {name},

You're one of our first 10 customers — thank you for taking a chance on ArkWatch!

🎁 YOUR EXCLUSIVE OFFER
You get 6 MONTHS of Pro access completely FREE (worth €174).

✅ YOUR ACCOUNT IS READY
Your account has been created automatically.

To activate your 6 months free trial:
1. Click this link: {checkout_url}
2. Complete the Stripe checkout (no payment required)
3. Start monitoring your websites immediately!

📊 WHAT YOU GET
✅ Unlimited website monitors
✅ Checks every 5 minutes
✅ AI-powered change summaries
✅ Email + SMS alerts
✅ Full API access
✅ Priority support (direct access to founder)

Your API Key: {api_key}
(Keep this safe - you'll need it to use the API)

🚀 NEXT STEPS
After completing checkout:
1. Go to your dashboard: https://arkforge.fr/dashboard.html
2. Add your first website to monitor
3. Get instant alerts when something changes

📅 NEED HELP GETTING STARTED?
Book a FREE 15-minute personalized demo with our founder:
👉 https://calendly.com/arkforge/demo

We'll help you:
• Set up your first monitors
• Configure alerts for your needs
• Maximize ArkWatch for your workflow

We'd love your feedback as you use ArkWatch. Reply to this email anytime.

After 6 months (on {time.strftime('%Y-%m-%d', time.gmtime(time.time() + 180*24*3600))}), you can:
• Continue with Pro at €29/month
• Downgrade to Free plan (3 monitors)
• Cancel completely

We'll send you a reminder 2 weeks before.

Questions? Just reply to this email.

— The ArkWatch Team
https://arkforge.fr
"""

        subprocess.run(
            [
                "python3",
                "/opt/claude-ceo/automation/email_sender.py",
                email,
                subject,
                body,
            ],
            timeout=10,
            check=False,
            capture_output=True,
        )
    except Exception:
        pass  # Best-effort


class FreeTrialSignup(BaseModel):
    email: str
    source: str = "direct"
    campaign: str = "free_trial_6months"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v


@router.post("/api/early-signup")
async def free_trial_signup(req: FreeTrialSignup, request: Request):
    """
    Collect email for 6 months free trial offer.
    Limited to first 10 signups.

    AUTOMATIC FLOW:
    1. Validates email and checks spots
    2. Creates full user account with API key
    3. Creates Stripe customer
    4. Generates Stripe Checkout session with 6MONTHSFREE promo
    5. Sends welcome email with checkout link
    6. Notifies CEO
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
            status_code=429, detail="Too many attempts. Please try again later."
        )
    _submit_attempts[client_ip].append(now)

    signups = _load_signups()

    # Check if spots are full
    if len(signups) >= MAX_SPOTS:
        return {
            "success": False,
            "message": f"Sorry, all {MAX_SPOTS} spots are taken. Join our waiting list instead.",
            "redirect": "/register.html?waitlist=true",
        }

    # Check duplicate in signups file
    if any(e["email"] == req.email for e in signups):
        # Check if user account already exists
        existing_user = get_user_by_email(req.email)
        if existing_user:
            return {
                "success": True,
                "message": "You're already registered! Check your email for your checkout link.",
            }

    # Extract name from email (fallback if no name provided)
    # The email is the only field we have from the landing page form
    name_from_email = req.email.split('@')[0].capitalize()

    # Check if user account already exists (before creating)
    existing_user = get_user_by_email(req.email)

    if existing_user:
        # User exists, just add to signups tracking if not already there
        if not any(e["email"] == req.email for e in signups):
            signups.append({
                "email": req.email,
                "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "ip": client_ip,
                "source": req.source,
                "campaign": req.campaign,
                "user_agent": request.headers.get("user-agent", ""),
                "referer": request.headers.get("referer", ""),
                "account_created": True,
                "api_key_created": True,
            })
            _save_signups(signups)

        return {
            "success": True,
            "message": "Account already exists! Check your email for next steps.",
        }

    # Create full user account with API key
    try:
        raw_key, key_hash, verification_code = create_api_key(
            name=name_from_email,
            email=req.email,
            tier="free",  # Start with free, will upgrade via Stripe
            privacy_accepted=True,
            client_ip=client_ip,
            signup_source=f"{req.source}_freetrial",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create account: {str(e)}"
        )

    # Create Stripe customer
    try:
        customer_id = StripeService.create_customer(
            email=req.email,
            name=name_from_email,
            api_key_hash=key_hash,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create billing account: {str(e)}"
        )

    # Create Stripe Checkout session with 6MONTHSFREE promo code
    # The promo code "6MONTHSFREE" must exist in Stripe dashboard
    checkout_url = ""
    try:
        session = StripeService.create_checkout_session(
            customer_id=customer_id,
            tier="pro",
            success_url="https://arkforge.fr/dashboard.html?welcome=true&plan=pro_6months_free",
            cancel_url="https://arkforge.fr/free-trial?checkout=cancelled",
            promotion_code="6MONTHSFREE",
            trial_days=0,  # No trial, promo code handles the 6 months free
        )
        checkout_url = session["checkout_url"]
    except Exception as e:
        # Log error but don't fail the signup - user can upgrade manually later
        checkout_url = "https://arkforge.fr/dashboard.html?upgrade=true"
        print(f"Warning: Failed to create Stripe checkout session for {req.email}: {e}")

    # Add to signups tracking
    signups.append({
        "email": req.email,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": client_ip,
        "source": req.source,
        "campaign": req.campaign,
        "user_agent": request.headers.get("user-agent", ""),
        "referer": request.headers.get("referer", ""),
        "account_created": True,
        "api_key": raw_key[:20] + "...",  # Truncated for tracking
        "stripe_customer_id": customer_id,
        "checkout_url": checkout_url,
    })
    _save_signups(signups)

    spots_left = MAX_SPOTS - len(signups)

    # Send early adopter welcome email with checkout link
    _send_early_adopter_welcome_email(req.email, name_from_email, raw_key, checkout_url)

    # Notify CEO of new signup
    _notify_ceo_new_signup(req.email, req.source, spots_left, raw_key)

    return {
        "success": True,
        "message": "Success! Check your email to activate your 6 months free trial.",
        "spots_left": spots_left,
        "checkout_url": checkout_url,  # Return checkout URL for immediate redirect
    }


@router.get("/api/free-trial/spots")
async def get_remaining_spots():
    """Get number of remaining spots for free trial offer."""
    signups = _load_signups()
    remaining = max(0, MAX_SPOTS - len(signups))

    return {
        "total": MAX_SPOTS,
        "taken": len(signups),
        "remaining": remaining,
        "available": remaining > 0,
    }


@router.get("/free-trial")
async def serve_free_trial_page():
    """Serve the free trial landing page HTML."""
    html_path = Path("/opt/claude-ceo/workspace/arkwatch/site/free-trial.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(html_path, media_type="text/html")
