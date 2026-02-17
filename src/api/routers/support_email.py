"""
Mailgun Inbound Email Handler for contact@arkforge.fr
Receives and processes support emails via webhook
"""

from fastapi import APIRouter, Form, Request, HTTPException
import hmac
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

router = APIRouter()

SUPPORT_EMAILS_DIR = Path("/opt/claude-ceo/workspace/arkwatch/support_emails")
SUPPORT_EMAILS_DIR.mkdir(exist_ok=True)


@router.post("/api/support/email/receive")
async def receive_support_email(
    request: Request,
    recipient: str = Form(...),
    sender: str = Form(...),
    subject: str = Form(default=""),
    stripped_text: str = Form(default="", alias="body-plain"),
    stripped_html: str = Form(default="", alias="body-html"),
    timestamp: str = Form(...),
    token: str = Form(...),
    signature: str = Form(...)
):
    """
    Receive inbound emails from Mailgun for contact@arkforge.fr

    Mailgun webhook sends POST with:
    - recipient: contact@arkforge.fr
    - sender: sender email
    - subject: email subject
    - body-plain: text content
    - body-html: HTML content
    - timestamp, token, signature: for verification
    """

    # 1. Verify webhook signature (CRITICAL for security)
    api_key = os.getenv('MAILGUN_API_KEY', '')

    if api_key:
        computed_signature = hmac.new(
            key=api_key.encode(),
            msg=f'{timestamp}{token}'.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, computed_signature):
            print(f"[SECURITY] Invalid Mailgun signature from {sender}")
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        print("[WARNING] MAILGUN_API_KEY not set - signature verification disabled")

    # 2. Save email to file system
    email_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{token[:8]}"
    email_data = {
        "id": email_id,
        "received_at": datetime.utcnow().isoformat(),
        "from": sender,
        "to": recipient,
        "subject": subject,
        "body_text": stripped_text,
        "body_html": stripped_html,
        "timestamp": timestamp,
        "token": token
    }

    # Save as JSON
    email_file = SUPPORT_EMAILS_DIR / f"{email_id}.json"
    with open(email_file, 'w', encoding='utf-8') as f:
        json.dump(email_data, f, indent=2, ensure_ascii=False)

    print(f"[INBOUND EMAIL] Saved: {email_id}")
    print(f"  From: {sender}")
    print(f"  Subject: {subject}")
    print(f"  Body preview: {stripped_text[:100]}...")

    # 3. TODO: Forward to Telegram / Create support ticket / Notify CEO
    # For now, just log and save to file

    # 4. Respond 200 OK (Mailgun expects quick response < 2s)
    return {
        "status": "received",
        "message_id": token,
        "saved_as": email_id
    }


@router.get("/api/support/email/list")
async def list_support_emails():
    """
    List all received support emails (for admin)
    """
    emails = []
    for email_file in sorted(SUPPORT_EMAILS_DIR.glob("*.json"), reverse=True):
        with open(email_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            emails.append({
                "id": data["id"],
                "from": data["from"],
                "subject": data["subject"],
                "received_at": data["received_at"]
            })

    return {"emails": emails, "total": len(emails)}


@router.get("/api/support/email/{email_id}")
async def get_support_email(email_id: str):
    """
    Get full email content by ID
    """
    email_file = SUPPORT_EMAILS_DIR / f"{email_id}.json"

    if not email_file.exists():
        raise HTTPException(status_code=404, detail="Email not found")

    with open(email_file, 'r', encoding='utf-8') as f:
        return json.load(f)
