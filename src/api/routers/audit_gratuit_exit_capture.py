"""API endpoint - Capture email visiteurs audit-gratuit qui partent sans signup.

Exit-intent popup côté client envoie l'email ici.
Envoie immédiatement un email de relance J+0 (booking link + 3 questions monitoring).
Les leads capturés sont ensuite ciblés par aggressive_audit_conversion.py (séquence J+1/J+2).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr

sys.path.insert(0, "/opt/claude-ceo/automation")

try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

router = APIRouter()

CAPTURE_FILE = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_exit_captures.json"
BOOKING_URL = "https://calendly.com/arkforge/audit-monitoring-15min"
AUDIT_PAGE_URL = "https://arkforge.fr/audit-gratuit-monitoring.html"


class ExitCaptureRequest(BaseModel):
    email: EmailStr
    visitor_id: str
    time_on_page: int = 0
    scroll_depth: int = 0
    form_started: bool = False


class ExitCaptureResponse(BaseModel):
    status: str
    message: str


def load_captures() -> dict:
    path = Path(CAPTURE_FILE)
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"captures": [], "created_at": datetime.now(timezone.utc).isoformat()}


def save_captures(data: dict):
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    path = Path(CAPTURE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def send_relance_j0(email: str, capture: dict):
    """Send immediate J+0 relance email to exit-intent visitor.

    Template: 'Vous etiez sur la page audit gratuit, besoin d'aide?
    Voici lien direct booking 15min + 3 questions monitoring'
    """
    if not EMAIL_ENABLED:
        print(f"[DRY RUN] Would send J+0 relance to {email}")
        return False

    time_on_page = capture.get("time_on_page", 0)
    time_min = time_on_page // 60
    time_sec = time_on_page % 60
    time_str = f"{time_min}min {time_sec:02d}s" if time_min else f"{time_sec}s"

    tracking_id = f"exit_relance_j0_{capture.get('visitor_id', 'unknown')}"
    tracking_pixel = (
        f'<img src="https://watch.arkforge.fr/api/track-email-open/{tracking_id}" '
        f'width="1" height="1" style="display:none;" alt="" />'
    )

    subject = "Votre audit monitoring gratuit vous attend"

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;">

<div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 22px;">Vous etiez sur notre page audit gratuit</h1>
    <p style="margin: 8px 0 0; opacity: 0.9;">On a remarque que vous n'avez pas finalise votre demande</p>
</div>

<div style="background: white; padding: 25px; border-radius: 12px; border: 1px solid #e5e7eb;">
    <p>Bonjour,</p>

    <p>Vous avez passe <strong>{time_str}</strong> sur notre page d'audit gratuit monitoring &mdash; c'est que le sujet vous parle.</p>

    <p>Pas de probleme si vous n'avez pas eu le temps de remplir le formulaire. Voici 2 options rapides :</p>

    <div style="background: #f0fdf4; padding: 18px; border-radius: 10px; border-left: 4px solid #22c55e; margin: 20px 0;">
        <p style="margin: 0 0 10px; font-weight: 700; color: #166534;">Option 1 : Reservez 15 min avec un expert</p>
        <a href="{BOOKING_URL}" style="display: inline-block; background: linear-gradient(135deg, #22c55e, #16a34a); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 700;">Booking 15 min gratuit</a>
    </div>

    <div style="background: #eff6ff; padding: 18px; border-radius: 10px; border-left: 4px solid #3b82f6; margin: 20px 0;">
        <p style="margin: 0 0 10px; font-weight: 700; color: #1e40af;">Option 2 : Finalisez votre audit gratuit</p>
        <a href="{AUDIT_PAGE_URL}?utm_source=relance_j0&utm_campaign=exit_intent" style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 700;">Reprendre mon audit</a>
    </div>

    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">

    <h3 style="font-size: 1.05rem; color: #1a1a1a; margin-bottom: 12px;">3 questions rapides pour mieux comprendre votre monitoring :</h3>
    <ol style="padding-left: 20px; color: #374151;">
        <li style="margin-bottom: 8px;"><strong>Combien de temps</strong> avant que votre equipe detecte une panne ? (heures, minutes, secondes ?)</li>
        <li style="margin-bottom: 8px;"><strong>Quel pourcentage</strong> de vos endpoints critiques est surveille en continu ?</li>
        <li style="margin-bottom: 8px;"><strong>Avez-vous deja perdu un client</strong> a cause d'un incident non detecte ?</li>
    </ol>
    <p style="color: #6b7280; font-size: 0.9rem;">Repondez simplement a cet email &mdash; on vous repond sous 2h.</p>

    <p style="margin-top: 20px;">A bientot,<br><strong>L'equipe ArkForge</strong></p>
</div>

<div style="text-align: center; padding: 15px 0; color: #9ca3af; font-size: 12px;">
    <a href="https://arkforge.fr" style="color: #6366f1; text-decoration: none;">ArkForge</a> &bull;
    <a href="https://arkforge.fr/legal/privacy.html" style="color: #6366f1; text-decoration: none;">Confidentialite</a>
    <br><span style="font-size: 11px;">Vous recevez cet email car vous avez laisse votre adresse sur notre page audit gratuit.</span>
</div>
{tracking_pixel}
</body></html>"""

    text_body = (
        f"Bonjour,\n\n"
        f"Vous avez passe {time_str} sur notre page d'audit gratuit monitoring.\n"
        f"Pas de probleme si vous n'avez pas eu le temps de finaliser.\n\n"
        f"Option 1 : Reservez 15 min avec un expert : {BOOKING_URL}\n"
        f"Option 2 : Finalisez votre audit gratuit : {AUDIT_PAGE_URL}\n\n"
        f"3 questions rapides :\n"
        f"1. Combien de temps avant que votre equipe detecte une panne ?\n"
        f"2. Quel pourcentage de vos endpoints critiques est surveille ?\n"
        f"3. Avez-vous deja perdu un client a cause d'un incident non detecte ?\n\n"
        f"Repondez simplement a cet email, on vous repond sous 2h.\n\n"
        f"L'equipe ArkForge"
    )

    try:
        result = send_email(
            to_addr=email,
            subject=subject,
            body=text_body,
            html_body=html_body,
            reply_to="contact@arkforge.fr",
            skip_warmup=True,
        )
        if result:
            print(f"[EXIT-RELANCE J+0] Email sent to {email}")
        return result
    except Exception as e:
        print(f"[EXIT-RELANCE J+0] Error sending to {email}: {e}")
        return False


@router.post("/api/audit-gratuit-exit-capture", response_model=ExitCaptureResponse)
async def capture_exit_email(
    req: ExitCaptureRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Capture email from exit-intent popup on audit-gratuit page.
    Sends immediate J+0 relance email with booking link + 3 monitoring questions.
    """
    data = load_captures()

    # Check duplicate email
    existing_emails = {c["email"].lower() for c in data["captures"]}
    if req.email.lower() in existing_emails:
        return ExitCaptureResponse(status="duplicate", message="Email already captured")

    # Also check if this email already submitted the audit form
    audit_tracking_file = Path("/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json")
    if audit_tracking_file.exists():
        try:
            with open(audit_tracking_file) as f:
                audit_data = json.load(f)
            submitted_emails = {s["email"].lower() for s in audit_data.get("submissions", [])}
            if req.email.lower() in submitted_emails:
                return ExitCaptureResponse(status="already_submitted", message="Already submitted audit form")
        except (json.JSONDecodeError, OSError):
            pass

    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )

    capture = {
        "email": req.email,
        "visitor_id": req.visitor_id,
        "time_on_page": req.time_on_page,
        "scroll_depth": req.scroll_depth,
        "form_started": req.form_started,
        "ip": client_ip,
        "user_agent": request.headers.get("user-agent", ""),
        "referrer": request.headers.get("referer", ""),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sequence_started": True,
        "sequence_step": 1,
        "relance_j0_sent": False,
        "relance_j0_sent_at": None,
    }

    data["captures"].append(capture)
    save_captures(data)

    # Send J+0 relance email in background (non-blocking for API response)
    background_tasks.add_task(_send_and_update_capture, req.email, capture, data)

    return ExitCaptureResponse(status="ok", message="Email captured for follow-up")


def _send_and_update_capture(email: str, capture: dict, data: dict):
    """Background task: send relance email and update capture record."""
    success = send_relance_j0(email, capture)
    if success:
        # Update the capture record with send status
        for c in data["captures"]:
            if c["email"].lower() == email.lower() and c["visitor_id"] == capture["visitor_id"]:
                c["relance_j0_sent"] = True
                c["relance_j0_sent_at"] = datetime.now(timezone.utc).isoformat()
                break
        save_captures(data)
