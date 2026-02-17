"""Authentication endpoints - self-service registration and account management"""

import re
import subprocess
import time
from collections import defaultdict
from html import escape as html_escape

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator

from ...billing.stripe_service import StripeService
from ...storage import get_db
from ..auth import (
    create_api_key,
    delete_api_key_by_email,
    disable_notifications_for_user,
    get_current_user,
    get_user_by_email,
    regenerate_verification_code,
    update_user_data,
    verify_unsubscribe_token,
    verify_user_email,
)

router = APIRouter()

# Simple in-memory rate limiting: max 3 registrations per IP per hour
_registration_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600  # 1 hour
RATE_LIMIT_MAX = 3

# Rate limiting for verify-email: max 5 attempts per email per 15 minutes
_verify_attempts: dict[str, list[float]] = defaultdict(list)
VERIFY_RATE_LIMIT_WINDOW = 900  # 15 minutes
VERIFY_RATE_LIMIT_MAX = 5

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
EMAIL_SENDER = "/opt/claude-ceo/automation/email_sender.py"


def _send_verification_email(email: str, name: str, code: str):
    """Send verification code via email (best-effort, non-blocking)."""
    subject = f"ArkWatch - Votre code de verification: {code}"
    body = (
        f"Bonjour {name},\n\n"
        f"Votre code de verification ArkWatch est: {code}\n\n"
        f"Ce code est valable 24 heures.\n"
        f"Verifiez via POST /api/v1/auth/verify-email avec votre email et ce code.\n\n"
        f"-- ArkWatch (https://arkforge.fr)"
    )
    try:
        subprocess.Popen(
            ["python3", EMAIL_SENDER, email, subject, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # Best-effort


def _send_onboarding_email(email: str, name: str, api_key: str = ""):
    """Send welcome/onboarding email after registration (best-effort, non-blocking)."""
    subject = f"Bienvenue {name} ! Demarrez avec ArkWatch en 2 minutes"
    body = (
        f"Bonjour {name},\n\n"
        f"Felicitations, votre compte ArkWatch est cree ! Vous etes pret(e) a "
        f"surveiller vos pages web et recevoir des alertes intelligentes.\n\n"
        f"Voici comment demarrer en 3 etapes simples :\n\n"
        f"--- ETAPE 1 : Verifiez votre email ---\n"
        f"Un code a 6 chiffres vous a ete envoye dans un email separe.\n"
        f"Entrez-le sur votre dashboard pour activer votre compte.\n\n"
        f"--- ETAPE 2 : Ajoutez votre premiere page a surveiller ---\n"
        f"Rendez-vous sur votre dashboard et cliquez \"Ajouter un monitor\".\n"
        f"Collez l'URL de la page que vous voulez surveiller, c'est tout !\n\n"
        f"--- ETAPE 3 : Recevez vos alertes ---\n"
        f"Des qu'un changement est detecte sur votre page, vous recevez\n"
        f"un email avec un resume IA de ce qui a change. Zero effort.\n\n"
        f">> Acceder a mon dashboard : https://arkforge.fr/dashboard.html\n\n"
        f"Votre offre gratuite inclut 3 URLs surveillees.\n"
        f"Besoin de plus ? Decouvrez nos offres : https://arkforge.fr/arkwatch.html\n\n"
        f"Besoin d'aide ?\n"
        f"- Repondez directement a cet email\n"
        f"- Ecrivez-nous : contact@arkforge.fr\n"
        f"- Documentation API : https://arkforge.fr/arkwatch.html#api\n\n"
        f"A bientot sur ArkWatch !\n"
        f"-- L'equipe ArkForge\n"
        f"https://arkforge.fr"
    )
    html_body = _build_onboarding_html(name, api_key)
    try:
        subprocess.Popen(
            ["python3", EMAIL_SENDER, email, subject, body, html_body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # Best-effort


def _build_onboarding_html(name: str, api_key: str = "") -> str:
    """Build HTML version of the onboarding welcome email."""
    safe_name = html_escape(name)
    api_key_section = ""
    if api_key:
        safe_key = html_escape(api_key)
        api_key_section = f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin:15px 0 5px;">
  <tr><td style="background-color:#f0f4ff;border:1px solid #d0daf0;border-radius:6px;padding:12px 16px;">
    <p style="margin:0 0 4px;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Votre cle API</p>
    <code style="font-size:14px;color:#1a73e8;word-break:break-all;">{safe_key}</code>
  </td></tr>
  </table>"""
    return f"""\
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f4f7fa;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f7fa;padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;max-width:600px;width:100%;">

<!-- Header -->
<tr><td style="background-color:#1a73e8;padding:30px 40px;text-align:center;">
  <h1 style="color:#ffffff;margin:0;font-size:24px;">Bienvenue {safe_name} !</h1>
  <p style="color:#e0e0e0;margin:8px 0 0;font-size:14px;">Demarrez avec ArkWatch en 2 minutes</p>
</td></tr>

<!-- Body -->
<tr><td style="padding:30px 40px;">
  <p style="font-size:16px;color:#333;line-height:1.6;">
    Felicitations, votre compte est cree ! Vous etes pret(e) a surveiller vos pages web
    et recevoir des alertes intelligentes.
  </p>
  {api_key_section}

  <p style="font-size:15px;color:#555;line-height:1.6;margin-top:20px;">
    Voici les <strong>3 etapes</strong> pour demarrer :
  </p>

  <!-- Step 1 -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr>
    <td width="50" valign="top" style="padding-right:15px;">
      <div style="width:40px;height:40px;border-radius:50%;background-color:#1a73e8;color:#fff;text-align:center;line-height:40px;font-size:18px;font-weight:bold;">1</div>
    </td>
    <td valign="top">
      <p style="margin:0 0 4px;font-size:15px;font-weight:bold;color:#333;">Verifiez votre email</p>
      <p style="margin:0;font-size:14px;color:#666;line-height:1.5;">Un code a 6 chiffres vous a ete envoye dans un email separe. Entrez-le sur votre <a href="https://arkforge.fr/dashboard.html" style="color:#1a73e8;text-decoration:none;">dashboard</a> pour activer votre compte.</p>
    </td>
  </tr>
  </table>

  <!-- Step 2 -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr>
    <td width="50" valign="top" style="padding-right:15px;">
      <div style="width:40px;height:40px;border-radius:50%;background-color:#1a73e8;color:#fff;text-align:center;line-height:40px;font-size:18px;font-weight:bold;">2</div>
    </td>
    <td valign="top">
      <p style="margin:0 0 4px;font-size:15px;font-weight:bold;color:#333;">Ajoutez votre premiere page</p>
      <p style="margin:0;font-size:14px;color:#666;line-height:1.5;">Sur le dashboard, cliquez <strong>&laquo; Ajouter un monitor &raquo;</strong> et collez l'URL de la page que vous voulez surveiller. C'est tout !</p>
    </td>
  </tr>
  </table>

  <!-- Step 3 -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr>
    <td width="50" valign="top" style="padding-right:15px;">
      <div style="width:40px;height:40px;border-radius:50%;background-color:#1a73e8;color:#fff;text-align:center;line-height:40px;font-size:18px;font-weight:bold;">3</div>
    </td>
    <td valign="top">
      <p style="margin:0 0 4px;font-size:15px;font-weight:bold;color:#333;">Recevez vos alertes</p>
      <p style="margin:0;font-size:14px;color:#666;line-height:1.5;">Des qu'un changement est detecte, vous recevez un email avec un <strong>resume IA</strong> de ce qui a change. Zero effort de votre cote.</p>
    </td>
  </tr>
  </table>

  <hr style="border:none;border-top:1px solid #e0e0e0;margin:25px 0;">

  <!-- Dashboard CTA -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:10px 0;">
    <a href="https://arkforge.fr/dashboard.html" style="display:inline-block;background-color:#1a73e8;color:#ffffff;text-decoration:none;padding:14px 35px;border-radius:6px;font-size:16px;font-weight:bold;">Acceder a mon Dashboard</a>
  </td></tr>
  </table>

  <!-- Free tier info -->
  <p style="font-size:13px;color:#888;text-align:center;margin-top:20px;">
    Votre offre gratuite inclut 3 URLs surveillees.
    <a href="https://arkforge.fr/arkwatch.html" style="color:#1a73e8;text-decoration:none;">Decouvrir nos offres</a>
  </p>
</td></tr>

<!-- Footer -->
<tr><td style="background-color:#f8f9fa;padding:20px 40px;text-align:center;border-top:1px solid #e0e0e0;">
  <p style="margin:0;font-size:13px;color:#666;">
    Besoin d'aide ? Repondez a cet email ou ecrivez-nous a
    <a href="mailto:contact@arkforge.fr" style="color:#1a73e8;text-decoration:none;">contact@arkforge.fr</a>
  </p>
  <p style="margin:10px 0 0;font-size:13px;color:#999;">
    <a href="https://arkforge.fr/arkwatch.html#api" style="color:#1a73e8;text-decoration:none;">Documentation API</a>
  </p>
  <p style="margin:8px 0 0;font-size:12px;color:#bbb;">
    ArkWatch par <a href="https://arkforge.fr" style="color:#999;text-decoration:none;">ArkForge</a>
  </p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _check_rate_limit(ip: str):
    now = time.time()
    # Clean old entries
    _registration_attempts[ip] = [t for t in _registration_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_registration_attempts[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many registration attempts. Try again later.")
    _registration_attempts[ip].append(now)


class RegisterRequest(BaseModel):
    email: str
    name: str
    privacy_accepted: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v) or len(v) > 254:
            raise ValueError("Invalid email address")
        return v

    @model_validator(mode="after")
    def validate_privacy(self):
        if not self.privacy_accepted:
            raise ValueError(
                "You must accept the privacy policy (privacy_accepted: true). See https://arkforge.fr/privacy"
            )
        return self


class RegisterResponse(BaseModel):
    api_key: str
    email: str
    name: str
    tier: str
    message: str
    privacy_policy: str = "https://arkforge.fr/privacy"


@router.post("/api/v1/auth/register", response_model=RegisterResponse)
async def register(req: RegisterRequest, request: Request):
    """Register for a free API key. No credit card required."""
    # Rate limit (use X-Real-IP from nginx, fallback to client.host)
    client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    _check_rate_limit(client_ip)

    # Validate name
    name = req.name.strip()
    if len(name) < 2 or len(name) > 100:
        raise HTTPException(status_code=400, detail="Name must be 2-100 characters")

    # Check if email already registered
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=409, detail="Email already registered. Contact contact@arkforge.fr if you lost your key."
        )

    # Capture signup source from query parameter ?ref=
    signup_source = request.query_params.get("ref", "direct")

    # Create free tier API key (returns raw_key, key_hash, verification_code)
    raw_key, _, verification_code = create_api_key(
        name=name,
        email=req.email,
        tier="free",
        privacy_accepted=True,
        client_ip=client_ip,
        signup_source=signup_source,
    )

    # Send verification email + onboarding welcome email
    _send_verification_email(req.email, name, verification_code)
    _send_onboarding_email(req.email, name, api_key=raw_key)

    return RegisterResponse(
        api_key=raw_key,
        email=req.email,
        name=name,
        tier="free",
        message="Welcome! A verification code has been sent to your email. Verify via POST /api/v1/auth/verify-email.",
    )


class UpdateAccountRequest(BaseModel):
    name: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) < 2 or len(v) > 100:
                raise ValueError("Name must be 2-100 characters")
        return v


@router.patch("/api/v1/auth/account")
async def update_account(req: UpdateAccountRequest, user: dict = Depends(get_current_user)):
    """Update your account information (GDPR Art. 16 - Right to rectification)."""
    updates = {}
    if req.name is not None:
        updates["name"] = req.name

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update. Provide at least 'name'.")

    email = user["email"]
    if not update_user_data(email, **updates):
        raise HTTPException(status_code=404, detail="Account not found.")

    return {
        "status": "updated",
        "updated_fields": list(updates.keys()),
        "message": "Account information updated successfully (GDPR Art. 16).",
    }


@router.delete("/api/v1/auth/account")
async def delete_account(user: dict = Depends(get_current_user)):
    """Delete your account and all associated data (GDPR Art. 17 - Right to erasure).
    This action is irreversible. All watches, reports, and your API key will be permanently deleted."""
    email = user["email"]

    # Cancel Stripe subscription if active
    stripe_cancelled = False
    subscription_id = user.get("stripe_subscription_id")
    if subscription_id:
        try:
            StripeService.cancel_subscription(subscription_id, at_period_end=False)
            stripe_cancelled = True
        except Exception:
            pass  # Best-effort: proceed with deletion even if Stripe fails

    # Delete all user data (watches + reports)
    db = get_db()
    result = db.delete_user_data(email)

    # Delete the API key itself
    delete_api_key_by_email(email)

    return {
        "status": "deleted",
        "email": email,
        "data_deleted": result,
        "stripe_subscription_cancelled": stripe_cancelled,
        "message": "Your account and all associated data have been permanently deleted.",
    }


@router.get("/api/v1/auth/account/data")
async def export_account_data(user: dict = Depends(get_current_user)):
    """Export all your personal data (GDPR Art. 15 - Right of access).
    Returns all data we hold about you in JSON format."""
    email = user["email"]
    db = get_db()

    watches = db.get_watches_by_user(email)
    watch_ids = {w["id"] for w in watches}

    all_reports = db.get_reports()
    user_reports = [r for r in all_reports if r.get("watch_id") in watch_ids]

    return {
        "account": {
            "email": email,
            "name": user.get("name"),
            "tier": user.get("tier"),
            "created_at": user.get("created_at"),
            "requests_count": user.get("requests_count"),
            "privacy_accepted_at": user.get("privacy_accepted_at"),
        },
        "watches": watches,
        "reports": user_reports,
        "privacy_policy": "https://arkforge.fr/privacy",
        "message": "This is all the data we hold about you (GDPR Art. 15).",
    }


class VerifyEmailRequest(BaseModel):
    email: str
    code: str


@router.post("/api/v1/auth/verify-email")
async def verify_email(req: VerifyEmailRequest, request: Request):
    """Verify your email with the 6-digit code sent during registration."""
    email = req.email.strip().lower()

    # Rate limit by email to prevent brute-force on 6-digit codes
    now = time.time()
    _verify_attempts[email] = [t for t in _verify_attempts[email] if now - t < VERIFY_RATE_LIMIT_WINDOW]
    if len(_verify_attempts[email]) >= VERIFY_RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many verification attempts. Try again later.")
    _verify_attempts[email].append(now)

    if verify_user_email(email, req.code.strip()):
        # Clear attempts on success
        _verify_attempts.pop(email, None)
        return {"status": "verified", "message": "Email verified successfully. You can now use all API features."}
    raise HTTPException(status_code=400, detail="Invalid or expired verification code.")


class ResendVerificationRequest(BaseModel):
    email: str


@router.post("/api/v1/auth/resend-verification")
async def resend_verification(req: ResendVerificationRequest, request: Request):
    """Resend the verification code to your email."""
    client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    _check_rate_limit(client_ip)

    email = req.email.strip().lower()
    new_code = regenerate_verification_code(email)
    if new_code:
        user = get_user_by_email(email)
        name = user[1].get("name", "User") if user else "User"
        _send_verification_email(email, name, new_code)

    # Always return success to avoid email enumeration
    return {"status": "sent", "message": "If this email is registered and unverified, a new code has been sent."}


@router.get("/api/v1/auth/unsubscribe")
async def unsubscribe(email: str, token: str):
    """Unsubscribe from all email notifications (GDPR Art. 21 - Right to object).
    This disables notification emails for all your watches."""
    email = email.strip().lower()
    if not verify_unsubscribe_token(email, token):
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe link.")

    count = disable_notifications_for_user(email)
    return {
        "status": "unsubscribed",
        "watches_updated": count,
        "message": "You have been unsubscribed from all email notifications. You can re-enable them via the API.",
    }
