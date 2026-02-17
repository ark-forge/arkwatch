"""Trial Tracking Router - Track trial starts and activity for conversion pipeline."""

import json
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_user_by_email

router = APIRouter()

TRIAL_ACTIVITY_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/trial_activity.json")


def _load_trial_activity() -> dict:
    """Load trial activity data."""
    if not TRIAL_ACTIVITY_FILE.exists():
        return {"trials": {}, "last_check": None}
    try:
        with open(TRIAL_ACTIVITY_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"trials": {}, "last_check": None}


def _save_trial_activity(data: dict):
    """Save trial activity data."""
    TRIAL_ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(TRIAL_ACTIVITY_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    import os
    os.replace(tmp, str(TRIAL_ACTIVITY_FILE))


def _notify_trial_start(email: str):
    """Notify fondations when a trial user starts using the product."""
    subject = f"🎯 TRIAL STARTED - User active: {email}"
    body = f"""NOUVEAU TRIAL ACTIF - OPPORTUNITÉ DE CONVERSION

Email: {email}
Premier usage: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}

L'utilisateur vient de faire sa première action (création de watch ou API call).

🎯 ACTION RECOMMANDÉE:
1. Surveiller l'engagement dans les 48h
2. Envoyer email personnalisé de bienvenue si >3 watches
3. Proposer démo/onboarding
4. Préparer offre de conversion avant fin du trial (J+14)

Utiliser trial_tracker.py pour suivre l'activité:
cd /opt/claude-ceo/workspace/arkwatch/conversion
python3 trial_tracker.py

Dashboard: https://watch.arkforge.fr/api/trial-14d/stats
"""

    try:
        subprocess.run([
            "python3",
            "/opt/claude-ceo/automation/email_sender.py",
            "apps.desiorac@gmail.com",  # Fondations via CEO
            subject,
            body
        ], timeout=10, check=False, capture_output=True)
    except Exception:
        pass  # Best effort


class TrialStartRequest(BaseModel):
    email: str
    action: str  # "watch_created", "api_call", "dashboard_visit"
    metadata: dict | None = None


@router.post("/api/trial/start")
async def log_trial_start(req: TrialStartRequest, request: Request):
    """
    Log when a trial user starts using the product (first meaningful action).

    This endpoint is called when:
    - User creates their first watch
    - User makes their first API call
    - User visits dashboard for the first time

    Triggers alert to fondations for conversion follow-up.
    """
    email = req.email.strip().lower()

    # Verify user exists
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Load activity data
    activity_data = _load_trial_activity()
    trials = activity_data.get("trials", {})

    # Check if this is first activity for this trial
    is_first_activity = email not in trials or not trials[email].get("started")

    # Get client info
    client_ip = request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )

    # Update trial tracking
    if email not in trials:
        trials[email] = {}

    trials[email].update({
        "started": True,
        "started_at": trials[email].get("started_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "first_action": trials[email].get("first_action") or req.action,
        "last_activity": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_action": req.action,
        "activity_count": trials[email].get("activity_count", 0) + 1,
        "ip": client_ip,
    })

    if req.metadata:
        trials[email]["metadata"] = req.metadata

    activity_data["trials"] = trials
    _save_trial_activity(activity_data)

    # Notify fondations on first activity (conversion opportunity)
    if is_first_activity:
        _notify_trial_start(email)

    return {
        "success": True,
        "email": email,
        "is_first_activity": is_first_activity,
        "activity_count": trials[email]["activity_count"],
        "message": "Trial activity logged successfully"
    }


@router.get("/api/trial/activity/{email}")
async def get_trial_activity(email: str):
    """Get activity data for a specific trial user."""
    email = email.strip().lower()

    activity_data = _load_trial_activity()
    trials = activity_data.get("trials", {})

    if email not in trials:
        return {
            "email": email,
            "started": False,
            "activity_count": 0
        }

    return {
        "email": email,
        **trials[email]
    }


@router.get("/api/trial/stats")
async def get_trial_tracking_stats():
    """Get overall trial tracking statistics."""
    activity_data = _load_trial_activity()
    trials = activity_data.get("trials", {})

    started_count = sum(1 for t in trials.values() if t.get("started"))
    activated_count = sum(1 for t in trials.values() if t.get("activated"))
    converted_count = sum(1 for t in trials.values() if t.get("converted"))

    return {
        "total_tracked": len(trials),
        "started_trials": started_count,
        "activated_trials": activated_count,
        "converted_customers": converted_count,
        "conversion_rate": round(converted_count / started_count * 100, 1) if started_count > 0 else 0,
        "last_check": activity_data.get("last_check")
    }
