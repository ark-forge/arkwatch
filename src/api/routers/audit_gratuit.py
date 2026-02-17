"""Audit Gratuit Monitoring Router - Landing page form + webhook notification"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

# Add automation directory to path for email_sender
sys.path.insert(0, "/opt/claude-ceo/automation")

try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False
    print("Warning: email_sender not available for audit-gratuit, emails logged only")

router = APIRouter(prefix="/audit-gratuit")

# Data file for tracking audit requests
AUDIT_TRACKING_FILE = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json"
MAX_SLOTS = 5
NOTIFY_EMAIL = os.getenv("ARKWATCH_NOTIFY_EMAIL", "apps.desiorac@gmail.com")


class AuditRequest(BaseModel):
    """Audit gratuit form data"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    stack: str = Field(..., min_length=1, max_length=50)
    url: str = Field(..., min_length=8, max_length=500)
    pain_point: str = Field(default="", max_length=100)
    submission_id: str = Field(..., min_length=5, max_length=100)
    source: str = Field(default="landing_page")
    utm_source: str | None = Field(default=None)
    utm_campaign: str | None = Field(default=None)
    referrer: str | None = Field(default=None)
    timestamp: str | None = Field(default=None)


class AuditResponse(BaseModel):
    """Audit gratuit response"""
    success: bool
    message: str
    slots_remaining: int
    submission_id: str


def load_tracking() -> dict:
    """Load audit tracking data"""
    path = Path(AUDIT_TRACKING_FILE)
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "campaign": "audit_gratuit_monitoring",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "max_slots": MAX_SLOTS,
        "submissions": [],
    }


def save_tracking(data: dict):
    """Save audit tracking data atomically"""
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    path = Path(AUDIT_TRACKING_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def get_slots_remaining(data: dict) -> int:
    """Calculate remaining slots"""
    used = len(data.get("submissions", []))
    return max(0, data.get("max_slots", MAX_SLOTS) - used)


def send_notification_webhook(submission: dict):
    """Send instant notification email to team about new audit request"""
    if not EMAIL_ENABLED:
        print(f"[DRY RUN] Would notify team about audit request from {submission['email']}")
        return

    subject = f"[AUDIT GRATUIT] Nouveau lead: {submission['name']} ({submission['stack']})"

    html_body = f"""
<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;">
<div style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 22px;">Nouvel Audit Gratuit Demande</h1>
</div>
<div style="background: white; padding: 25px; border-radius: 12px; border: 1px solid #e5e7eb;">
    <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 8px 0; font-weight: 700; width: 120px;">Nom</td><td>{submission['name']}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Email</td><td><a href="mailto:{submission['email']}">{submission['email']}</a></td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Stack</td><td>{submission['stack']}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">URL</td><td><a href="{submission['url']}">{submission['url']}</a></td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Pain point</td><td>{submission.get('pain_point', 'N/A')}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Source</td><td>{submission.get('source', 'direct')}</td></tr>
        <tr><td style="padding: 8px 0; font-weight: 700;">Date</td><td>{submission['submitted_at']}</td></tr>
    </table>
    <div style="margin-top: 15px; padding: 12px; background: #fef2f2; border-radius: 8px; border-left: 4px solid #dc2626;">
        <strong>Action requise:</strong> Livrer rapport PDF audit sous 48h a {submission['email']}
    </div>
</div>
</body></html>
"""

    try:
        send_email(
            to_addr=NOTIFY_EMAIL,
            subject=subject,
            body=f"Nouvel audit gratuit: {submission['name']} - {submission['email']} - {submission['stack']} - {submission['url']}",
            html_body=html_body,
            reply_to=submission['email'],
            skip_warmup=True,
        )
    except Exception as e:
        print(f"Error sending audit notification: {e}")


def send_confirmation_email(name: str, email: str, stack: str, url: str, submission_id: str):
    """Send confirmation email to the lead"""
    if not EMAIL_ENABLED:
        print(f"[DRY RUN] Would send audit confirmation to {email}")
        return

    tracking_pixel = f'<img src="https://watch.arkforge.fr/api/track-email-open/audit_gratuit_{submission_id}" width="1" height="1" style="display:none;" alt="" />'

    subject = "Votre audit monitoring gratuit est en cours"

    html_body = f"""
<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;">
<div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 24px;">Audit en cours !</h1>
    <p style="margin: 10px 0 0; opacity: 0.9;">Votre rapport arrive sous 48h</p>
</div>
<div style="background: white; padding: 25px; border-radius: 12px; border: 1px solid #e5e7eb;">
    <p>Bonjour <strong>{name}</strong>,</p>
    <p>Merci d'avoir reserve votre audit gratuit ! Notre equipe est deja en train d'analyser :</p>
    <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; border-left: 4px solid #6366f1; margin: 15px 0;">
        <p style="margin: 0;"><strong>URL :</strong> {url}</p>
        <p style="margin: 5px 0 0;"><strong>Stack :</strong> {stack}</p>
    </div>
    <h3 style="margin: 20px 0 10px;">Ce que vous recevrez :</h3>
    <ul style="padding-left: 20px;">
        <li>Analyse de couverture monitoring</li>
        <li>Benchmark temps de reponse multi-regions</li>
        <li>Score de maturite sur 100</li>
        <li>Plan d'action priorise</li>
    </ul>
    <p>Vous recevrez votre rapport PDF complet sous <strong>48 heures</strong>.</p>
    <p style="margin-top: 20px;">A bientot,<br><strong>L'equipe ArkForge</strong></p>
</div>
<div style="text-align: center; padding: 15px 0; color: #9ca3af; font-size: 12px;">
    <a href="https://arkforge.fr" style="color: #6366f1; text-decoration: none;">ArkForge</a> &bull;
    <a href="https://arkforge.fr/legal/privacy.html" style="color: #6366f1; text-decoration: none;">Confidentialite</a>
</div>
{tracking_pixel}
</body></html>
"""

    try:
        send_email(
            to_addr=email,
            subject=subject,
            body=f"Bonjour {name}, votre audit monitoring gratuit est en cours. Rapport PDF sous 48h.",
            html_body=html_body,
            reply_to="contact@arkforge.fr",
            skip_warmup=True,
        )
    except Exception as e:
        print(f"Error sending audit confirmation email: {e}")


@router.post("/submit", response_model=AuditResponse)
async def submit_audit(request: AuditRequest):
    """
    Handle audit gratuit form submission.
    Tracks submission, sends confirmation + team notification, manages slot count.
    """
    tracking = load_tracking()
    slots = get_slots_remaining(tracking)

    # Check slots
    if slots <= 0:
        raise HTTPException(
            status_code=409,
            detail="Offre complete. Les 5 places ont ete prises."
        )

    # Check duplicate email
    existing = next(
        (s for s in tracking["submissions"] if s["email"] == request.email),
        None
    )
    if existing:
        return AuditResponse(
            success=True,
            message="Vous etes deja inscrit ! Votre rapport arrive sous 48h.",
            slots_remaining=slots,
            submission_id=existing["submission_id"]
        )

    timestamp = request.timestamp or (datetime.utcnow().isoformat() + "Z")

    submission = {
        "submission_id": request.submission_id,
        "name": request.name,
        "email": request.email,
        "stack": request.stack,
        "url": request.url,
        "pain_point": request.pain_point,
        "source": request.source,
        "utm_source": request.utm_source,
        "utm_campaign": request.utm_campaign,
        "referrer": request.referrer,
        "submitted_at": timestamp,
        "confirmation_sent": False,
        "notification_sent": False,
        "report_delivered": False,
        "report_delivered_at": None,
    }

    # Send confirmation to lead
    send_confirmation_email(
        name=request.name,
        email=request.email,
        stack=request.stack,
        url=request.url,
        submission_id=request.submission_id,
    )
    submission["confirmation_sent"] = True

    # Send instant notification to team (webhook)
    send_notification_webhook(submission)
    submission["notification_sent"] = True

    # Save
    tracking["submissions"].append(submission)
    save_tracking(tracking)

    new_slots = get_slots_remaining(tracking)

    return AuditResponse(
        success=True,
        message="Audit reserve ! Consultez votre email pour la confirmation.",
        slots_remaining=new_slots,
        submission_id=request.submission_id,
    )


@router.get("/slots")
async def get_slots():
    """Get current slot availability"""
    tracking = load_tracking()
    slots = get_slots_remaining(tracking)
    total = len(tracking.get("submissions", []))

    return {
        "slots_remaining": slots,
        "slots_total": tracking.get("max_slots", MAX_SLOTS),
        "slots_used": total,
    }


@router.get("/stats")
async def audit_stats():
    """Get audit campaign statistics"""
    tracking = load_tracking()
    submissions = tracking.get("submissions", [])
    total = len(submissions)

    if total == 0:
        return {
            "total_submissions": 0,
            "slots_remaining": MAX_SLOTS,
            "confirmations_sent": 0,
            "reports_delivered": 0,
            "last_submission": None,
        }

    return {
        "total_submissions": total,
        "slots_remaining": get_slots_remaining(tracking),
        "confirmations_sent": sum(1 for s in submissions if s.get("confirmation_sent")),
        "reports_delivered": sum(1 for s in submissions if s.get("report_delivered")),
        "last_submission": max(s["submitted_at"] for s in submissions) if submissions else None,
    }
