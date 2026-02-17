"""Trial Signup Router - Handle trial signup form submissions with tracking"""

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
    print("Warning: email_sender not available, emails will be logged only")

router = APIRouter()

# Data file for tracking signups
SIGNUP_TRACKING_FILE = "/opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json"


class TrialSignupRequest(BaseModel):
    """Trial signup form data"""
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    usecase: str = Field(..., min_length=10, max_length=1000, description="What they will monitor")
    source: str = Field(default="direct", description="Traffic source")
    campaign: str = Field(default="trial_signup", description="Campaign identifier")
    submission_id: str = Field(..., description="Unique submission ID")
    utm_source: str | None = Field(default=None, description="UTM source")
    utm_campaign: str | None = Field(default=None, description="UTM campaign")
    referrer: str | None = Field(default=None, description="Referrer URL")
    timestamp: str | None = Field(default=None, description="Submission timestamp")


class TrialSignupResponse(BaseModel):
    """Trial signup response"""
    success: bool
    message: str
    redirect_url: str
    submission_id: str


def init_tracking_data():
    """Initialize tracking data structure"""
    tracking_file = Path(SIGNUP_TRACKING_FILE)

    if tracking_file.exists():
        try:
            with open(tracking_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # Default structure
    return {
        "campaign": "trial_signup",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "submissions": [],
        "metrics": {
            "total_submissions": 0,
            "total_emails_sent": 0,
            "total_conversions": 0,
            "conversion_rate": 0.0
        }
    }


def save_tracking_data(data: dict):
    """Save tracking data to file"""
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    tracking_file = Path(SIGNUP_TRACKING_FILE)
    tracking_file.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = tracking_file.with_suffix(".json.tmp")
    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=2)
    tmp_file.replace(tracking_file)


def send_trial_confirmation_email(name: str, email: str, usecase: str, submission_id: str) -> bool:
    """
    Send confirmation email with trial access link.

    Args:
        name: User's full name
        email: User's email address
        usecase: What they will monitor
        submission_id: Unique submission ID for tracking

    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED:
        print(f"[DRY RUN] Would send trial confirmation email to {email}")
        return False

    # Tracking pixel URL
    tracking_pixel = f'<img src="https://watch.arkforge.fr/api/track-email-open/trial_signup_{submission_id}" width="1" height="1" style="display:none;" alt="" />'

    subject = "🚀 Your ArkWatch Trial is Ready!"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
        <h1 style="margin: 0; font-size: 28px; font-weight: 900;">Welcome to ArkWatch! 🎉</h1>
        <p style="margin: 15px 0 0; font-size: 16px; opacity: 0.95;">Your 14-day free trial starts now</p>
    </div>

    <div style="background: white; padding: 30px; border-radius: 12px; border: 1px solid #e5e7eb;">
        <p style="margin: 0 0 15px; font-size: 16px;">Hi <strong>{name}</strong>,</p>

        <p style="margin: 0 0 15px; font-size: 16px;">
            Thanks for signing up! Your ArkWatch trial is ready. You mentioned you want to monitor:
        </p>

        <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; border-left: 4px solid #6366f1; margin: 20px 0;">
            <p style="margin: 0; font-style: italic; color: #374151;">"{usecase}"</p>
        </div>

        <p style="margin: 15px 0; font-size: 16px;">
            Let's get started! Click the button below to set up your first monitor:
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="https://arkforge.fr/try?email={email}&trial=true&ref=signup_{submission_id}"
               style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 16px 32px; font-size: 16px; font-weight: 700; border-radius: 10px; text-decoration: none;">
                Start Monitoring Now →
            </a>
        </div>

        <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 10px; font-size: 16px; font-weight: 700; color: #1a1a1a;">What's included in your trial:</h3>
            <ul style="margin: 0; padding-left: 20px;">
                <li style="margin: 8px 0;">Monitor up to 10 URLs</li>
                <li style="margin: 8px 0;">Check every 5 minutes</li>
                <li style="margin: 8px 0;">AI-powered change summaries</li>
                <li style="margin: 8px 0;">Instant email alerts</li>
                <li style="margin: 8px 0;">Priority support</li>
            </ul>
        </div>

        <p style="margin: 15px 0; font-size: 16px;">
            <strong>Need help getting started?</strong><br>
            Reply to this email anytime. I'm here to help!
        </p>

        <p style="margin: 20px 0 0; font-size: 16px;">
            Best,<br>
            <strong>ArkForge Team</strong>
        </p>
    </div>

    <div style="text-align: center; padding: 20px 0; color: #6b7280; font-size: 14px;">
        <p style="margin: 5px 0;">
            <a href="https://arkforge.fr" style="color: #6366f1; text-decoration: none;">ArkForge</a> •
            <a href="https://arkforge.fr/legal/privacy.html" style="color: #6366f1; text-decoration: none;">Privacy</a> •
            <a href="https://arkforge.fr/legal/terms.html" style="color: #6366f1; text-decoration: none;">Terms</a>
        </p>
        <p style="margin: 10px 0 0; color: #9ca3af; font-size: 12px;">
            © 2026 ArkForge. All rights reserved.
        </p>
    </div>

    {tracking_pixel}
</body>
</html>
"""

    try:
        send_email(
            to_addr=email,
            subject=subject,
            body="Your ArkWatch trial is ready! Check the HTML version of this email for details.",
            html_body=html_body,
            reply_to="contact@arkforge.fr",
            skip_warmup=True,
        )
        return True
    except Exception as e:
        print(f"Error sending trial confirmation email: {e}")
        return False


@router.post("/trial-signup", response_model=TrialSignupResponse)
async def trial_signup(request: TrialSignupRequest):
    """
    Handle trial signup form submission.

    Tracks submission, sends confirmation email with tracking pixel,
    and redirects user to /try page.
    """
    # Load tracking data
    tracking_data = init_tracking_data()

    # Check for duplicate email (prevent multiple trials)
    existing_submission = next(
        (s for s in tracking_data["submissions"] if s["email"] == request.email),
        None
    )

    if existing_submission:
        # Return existing submission (don't create duplicate)
        return TrialSignupResponse(
            success=True,
            message="Welcome back! Check your email for your trial access link.",
            redirect_url=f"https://arkforge.fr/try?email={request.email}&trial=true&ref=returning",
            submission_id=existing_submission["submission_id"]
        )

    # Create new submission record
    timestamp = request.timestamp or (datetime.utcnow().isoformat() + "Z")

    submission = {
        "submission_id": request.submission_id,
        "name": request.name,
        "email": request.email,
        "usecase": request.usecase,
        "source": request.source,
        "campaign": request.campaign,
        "utm_source": request.utm_source,
        "utm_campaign": request.utm_campaign,
        "referrer": request.referrer,
        "submitted_at": timestamp,
        "email_sent": False,
        "email_sent_at": None,
        "email_opened": False,
        "email_opened_at": None,
        "conversion_completed": False,
        "conversion_completed_at": None
    }

    # Send confirmation email
    email_sent = send_trial_confirmation_email(
        name=request.name,
        email=request.email,
        usecase=request.usecase,
        submission_id=request.submission_id
    )

    if email_sent:
        submission["email_sent"] = True
        submission["email_sent_at"] = datetime.utcnow().isoformat() + "Z"

    # Add to tracking data
    tracking_data["submissions"].append(submission)

    # Update metrics
    tracking_data["metrics"]["total_submissions"] += 1
    if email_sent:
        tracking_data["metrics"]["total_emails_sent"] += 1

    # Save tracking data
    save_tracking_data(tracking_data)

    # Return success response
    return TrialSignupResponse(
        success=True,
        message="Success! Check your email to get started.",
        redirect_url=f"https://arkforge.fr/try?email={request.email}&trial=true&ref=signup_{request.submission_id}",
        submission_id=request.submission_id
    )


@router.get("/trial-signup/stats")
async def trial_signup_stats():
    """Get trial signup statistics"""
    tracking_data = init_tracking_data()

    # Calculate additional metrics
    submissions = tracking_data["submissions"]
    total = len(submissions)

    if total == 0:
        return {
            "total_submissions": 0,
            "total_emails_sent": 0,
            "total_email_opens": 0,
            "total_conversions": 0,
            "email_send_rate": 0.0,
            "email_open_rate": 0.0,
            "conversion_rate": 0.0,
            "last_submission": None
        }

    emails_sent = sum(1 for s in submissions if s.get("email_sent"))
    emails_opened = sum(1 for s in submissions if s.get("email_opened"))
    conversions = sum(1 for s in submissions if s.get("conversion_completed"))

    email_send_rate = (emails_sent / total * 100) if total > 0 else 0.0
    email_open_rate = (emails_opened / emails_sent * 100) if emails_sent > 0 else 0.0
    conversion_rate = (conversions / total * 100) if total > 0 else 0.0

    # Get last submission
    last_submission = max(submissions, key=lambda s: s["submitted_at"]) if submissions else None

    return {
        "total_submissions": total,
        "total_emails_sent": emails_sent,
        "total_email_opens": emails_opened,
        "total_conversions": conversions,
        "email_send_rate": round(email_send_rate, 2),
        "email_open_rate": round(email_open_rate, 2),
        "conversion_rate": round(conversion_rate, 2),
        "last_submission": last_submission["submitted_at"] if last_submission else None
    }
