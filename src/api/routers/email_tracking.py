"""Email Tracking Router - Track email opens via pixel"""

import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

router = APIRouter()

# Use data directory that's accessible by the API service
TRACKING_FILE = "/opt/claude-ceo/workspace/arkwatch/data/outreach_email_tracking_20260209.json"
TRIAL_SIGNUP_TRACKING_FILE = "/opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json"


@router.get("/track-email-open/{lead_id}")
async def track_email_open(lead_id: str):
    """
    Track email open via 1x1 transparent pixel.

    Supports both legacy integer lead IDs and trial_signup_* string IDs.

    Args:
        lead_id: ID of the lead (int or 'trial_signup_<submission_id>')

    Returns:
        1x1 transparent PNG
    """
    # Route to appropriate tracking handler
    if isinstance(lead_id, str) and lead_id.startswith("nurturing_"):
        log_nurturing_email_open(lead_id)
    elif isinstance(lead_id, str) and lead_id.startswith("trial_signup_"):
        log_trial_signup_email_open(lead_id)
    else:
        # Legacy tracking for integer lead IDs
        try:
            log_email_open(int(lead_id))
        except ValueError:
            log_email_open(lead_id)

    # Return 1x1 transparent pixel
    pixel = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

    return Response(
        content=pixel,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


def log_email_open(lead_id: int):
    """
    Log email open to tracking file.

    Args:
        lead_id: ID of the lead
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Load tracking data
    try:
        if os.path.exists(TRACKING_FILE):
            with open(TRACKING_FILE, 'r') as f:
                tracking_data = json.load(f)
        else:
            tracking_data = {
                "task_id": "20260934",
                "campaign_name": "Outreach Email Direct - 15 DevOps/SRE Leaders",
                "created_date": "2026-02-09",
                "status": "scheduled",
                "leads": [],
                "metrics": {
                    "scheduled": 15,
                    "sent": 0,
                    "opened": 0,
                    "replied": 0,
                    "trials_activated": 0
                },
                "notes": []
            }
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback if file corrupted
        tracking_data = {
            "task_id": "20260934",
            "campaign_name": "Outreach Email Direct - 15 DevOps/SRE Leaders",
            "created_date": "2026-02-09",
            "status": "active",
            "leads": [],
            "metrics": {
                "scheduled": 15,
                "sent": 0,
                "opened": 0,
                "replied": 0,
                "trials_activated": 0
            },
            "notes": []
        }

    # Update lead data
    lead_found = False
    for lead in tracking_data.get("leads", []):
        if lead.get("id") == lead_id:
            lead_found = True

            # Initialize opens tracking
            if "opens" not in lead:
                lead["opens"] = []

            # Add new open event
            lead["opens"].append(timestamp)

            # Update opened timestamp if first open
            if lead.get("opened") is None:
                lead["opened"] = timestamp

                # Increment metrics counter
                tracking_data["metrics"]["opened"] = tracking_data["metrics"].get("opened", 0) + 1

            break

    # If lead not found, create entry
    if not lead_found:
        new_lead = {
            "id": lead_id,
            "opened": timestamp,
            "opens": [timestamp],
            "status": "opened"
        }
        tracking_data["leads"].append(new_lead)
        tracking_data["metrics"]["opened"] = tracking_data["metrics"].get("opened", 0) + 1

    # Add note
    note = f"{timestamp}: Lead {lead_id} opened email"
    if "notes" not in tracking_data:
        tracking_data["notes"] = []
    tracking_data["notes"].append(note)

    # Save updated tracking data
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)


def log_trial_signup_email_open(lead_id: str):
    """
    Log trial signup email open to tracking file.

    Args:
        lead_id: String like 'trial_signup_<submission_id>'
    """
    # Extract submission_id from lead_id
    submission_id = lead_id.replace("trial_signup_", "")
    timestamp = datetime.utcnow().isoformat() + "Z"

    tracking_file = Path(TRIAL_SIGNUP_TRACKING_FILE)

    # Load trial signup tracking data
    try:
        if tracking_file.exists():
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
        else:
            # Initialize if doesn't exist
            tracking_data = {
                "campaign": "trial_signup",
                "created_at": timestamp,
                "last_updated": timestamp,
                "submissions": [],
                "metrics": {
                    "total_submissions": 0,
                    "total_emails_sent": 0,
                    "total_conversions": 0,
                    "conversion_rate": 0.0
                }
            }
    except (FileNotFoundError, json.JSONDecodeError):
        tracking_data = {
            "campaign": "trial_signup",
            "created_at": timestamp,
            "last_updated": timestamp,
            "submissions": [],
            "metrics": {
                "total_submissions": 0,
                "total_emails_sent": 0,
                "total_conversions": 0,
                "conversion_rate": 0.0
            }
        }

    # Find submission by submission_id
    submission_found = False
    for submission in tracking_data.get("submissions", []):
        if submission.get("submission_id") == submission_id:
            submission_found = True

            # Initialize opens tracking
            if "email_opens" not in submission:
                submission["email_opens"] = []

            # Add new open event
            submission["email_opens"].append(timestamp)

            # Mark as opened if first open
            if not submission.get("email_opened"):
                submission["email_opened"] = True
                submission["email_opened_at"] = timestamp

            break

    # If submission not found, log warning but continue (pixel might be opened later)
    if not submission_found:
        print(f"Warning: Trial signup submission not found for ID: {submission_id}")
        # Create placeholder entry
        tracking_data["submissions"].append({
            "submission_id": submission_id,
            "email_opened": True,
            "email_opened_at": timestamp,
            "email_opens": [timestamp],
            "note": "Email opened before submission was recorded (race condition)"
        })

    # Update timestamp
    tracking_data["last_updated"] = timestamp

    # Save updated tracking data
    tracking_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = tracking_file.with_suffix(".json.tmp")
    with open(tmp_file, 'w') as f:
        json.dump(tracking_data, f, indent=2)
    tmp_file.replace(tracking_file)


NURTURING_STATE_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/nurturing_state.json")


def log_nurturing_email_open(lead_id: str):
    """
    Log nurturing sequence email open.

    Args:
        lead_id: String like 'nurturing_<email_safe>_<step_id>'
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Parse lead_id: nurturing_{email_safe}_{step_id}
    parts = lead_id.replace("nurturing_", "", 1)
    # Find step_id (last known step name)
    step_ids = [
        "day3_onboarding", "day7_use_cases", "day10_final_push",  # Current sequence
        "day2_case_study", "day5_expiry_reminder", "day7_last_chance", "day10_final_offer",  # Legacy
    ]
    step_id = None
    email_safe = parts
    for sid in step_ids:
        if parts.endswith(f"_{sid}"):
            step_id = sid
            email_safe = parts[: -(len(sid) + 1)]
            break

    # Load nurturing state
    state_file = NURTURING_STATE_FILE
    try:
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
        else:
            state = {"leads": {}, "metrics": {}}
    except (json.JSONDecodeError, OSError):
        state = {"leads": {}, "metrics": {}}

    # Find matching lead by email_safe pattern
    matched_email = None
    for email in state.get("leads", {}):
        safe = email.replace("@", "_at_").replace(".", "_")
        if safe == email_safe:
            matched_email = email
            break

    if matched_email and step_id:
        lead = state["leads"][matched_email]
        opens_key = "opens"
        if opens_key not in lead:
            lead[opens_key] = {}
        if step_id not in lead[opens_key]:
            lead[opens_key][step_id] = []
        lead[opens_key][step_id].append(timestamp)

        # Update metrics
        if "opens" not in state.get("metrics", {}):
            state.setdefault("metrics", {})["opens"] = {}
        state["metrics"]["opens"][step_id] = state["metrics"]["opens"].get(step_id, 0) + 1

        state["last_open"] = timestamp

        # Save
        state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_file.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(str(tmp), str(state_file))
    else:
        print(f"Warning: Nurturing open for unknown lead: {lead_id}")


CLICK_TRACKING_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/nurturing_clicks.json")

# Allowlist of redirect destinations to prevent open redirect
ALLOWED_CLICK_DOMAINS = {"arkforge.fr", "watch.arkforge.fr", "calendly.com"}


@router.get("/track-click/{lead_id}")
async def track_email_click(lead_id: str, url: str = ""):
    """Track email link click and redirect to destination URL.

    Args:
        lead_id: Tracking ID (e.g. 'nurturing_email_step')
        url: Destination URL to redirect to
    """
    from urllib.parse import urlparse

    # Validate URL against allowlist
    if not url:
        url = "https://arkforge.fr"
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_CLICK_DOMAINS:
        url = "https://arkforge.fr"

    # Log click
    timestamp = datetime.utcnow().isoformat() + "Z"
    try:
        clicks = {}
        if CLICK_TRACKING_FILE.exists():
            with open(CLICK_TRACKING_FILE) as f:
                clicks = json.load(f)

        if "clicks" not in clicks:
            clicks["clicks"] = []
        clicks["clicks"].append({
            "lead_id": lead_id,
            "url": url,
            "timestamp": timestamp,
        })
        clicks["last_click"] = timestamp
        clicks["total"] = len(clicks["clicks"])

        # Update nurturing state with click data
        if lead_id.startswith("nurturing_"):
            _log_nurturing_click(lead_id, url, timestamp)

        CLICK_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CLICK_TRACKING_FILE.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(clicks, f, indent=2)
        os.replace(str(tmp), str(CLICK_TRACKING_FILE))
    except Exception as e:
        print(f"Click tracking error: {e}")

    return RedirectResponse(url=url, status_code=302)


def _log_nurturing_click(lead_id: str, url: str, timestamp: str):
    """Log click in nurturing state for the matched lead."""
    parts = lead_id.replace("nurturing_", "", 1)
    step_ids = ["day3", "day3_calendly", "day7", "day10_checkout", "day2", "day5", "day10"]
    step_id = None
    email_safe = parts
    for sid in step_ids:
        if parts.endswith(f"_{sid}"):
            step_id = sid
            email_safe = parts[: -(len(sid) + 1)]
            break

    if not step_id:
        return

    try:
        if NURTURING_STATE_FILE.exists():
            with open(NURTURING_STATE_FILE) as f:
                state = json.load(f)
        else:
            return

        for email in state.get("leads", {}):
            safe = email.replace("@", "_at_").replace(".", "_")
            if safe == email_safe:
                lead = state["leads"][email]
                if "clicks" not in lead:
                    lead["clicks"] = {}
                if step_id not in lead["clicks"]:
                    lead["clicks"][step_id] = []
                lead["clicks"][step_id].append({"url": url, "at": timestamp})

                if "clicks" not in state.get("metrics", {}):
                    state.setdefault("metrics", {})["clicks"] = {}
                state["metrics"]["clicks"][step_id] = state["metrics"]["clicks"].get(step_id, 0) + 1

                tmp = NURTURING_STATE_FILE.with_suffix(".json.tmp")
                with open(tmp, "w") as f:
                    json.dump(state, f, indent=2)
                os.replace(str(tmp), str(NURTURING_STATE_FILE))
                break
    except Exception as e:
        print(f"Nurturing click log error: {e}")
