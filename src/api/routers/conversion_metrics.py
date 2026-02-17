"""Conversion Metrics Router - Trial-to-paid funnel dashboard with real-time metrics

Aggregates data from multiple sources to provide:
- Trial signups by source (Dev.to, LinkedIn, email, direct)
- Email nurturing open rates by step (J+0, J+2, J+5, J+7)
- CTA click tracking per nurturing email
- Trial → paid conversion tracking
- Average time from signup to conversion
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

# Data source paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
TRIAL_SIGNUPS_FILE = DATA_DIR / "trial_signups_tracking.json"
TRIAL_14D_FILE = DATA_DIR / "trial_14d_signups.json"
UNIFIED_TRACKING_FILE = DATA_DIR / "unified_email_tracking.json"
OUTREACH_TRACKING_FILE = DATA_DIR / "outreach_email_tracking_20260209.json"
NURTURING_STATE_FILE = DATA_DIR / "nurturing_state.json"
NURTURING_CLICKS_FILE = DATA_DIR / "nurturing_clicks.json"
PAGE_VISITS_FILE = DATA_DIR / "page_visits.jsonl"

# Dashboard HTML
FUNNEL_DASHBOARD_HTML = "/opt/claude-ceo/workspace/arkwatch/site/funnel-dashboard.html"

# Source mapping from UTM and referrer data
SOURCE_PATTERNS = {
    "devto": ["dev.to", "devto", "dev_to"],
    "linkedin": ["linkedin", "lnkd"],
    "email": ["email", "outreach", "cold_email", "nurturing", "trial_conversion"],
    "hackernews": ["hackernews", "hn", "news.ycombinator"],
    "twitter": ["twitter", "x.com", "t.co"],
}


def _load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return default


def _load_jsonl(path) -> list:
    entries = []
    try:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    except FileNotFoundError:
        pass
    return entries


def _classify_source(signup: dict) -> str:
    """Determine traffic source from UTM params, referrer, and campaign data."""
    utm = (signup.get("utm_source") or "").lower()
    campaign = (signup.get("campaign") or "").lower()
    referrer = (signup.get("referrer") or "").lower()
    source = (signup.get("source") or "").lower()

    combined = f"{utm} {campaign} {referrer} {source}"

    for source_name, patterns in SOURCE_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                return source_name

    return "direct"


def _get_trial_signups_by_source() -> dict:
    """Aggregate trial signups from both signup forms, grouped by source."""
    by_source = {}
    all_signups = []

    # Source 1: Trial signup form (trial_signups_tracking.json)
    form_data = _load_json(TRIAL_SIGNUPS_FILE, {"submissions": []})
    for sub in form_data.get("submissions", []):
        source = _classify_source(sub)
        signup = {
            "email": sub.get("email", ""),
            "name": sub.get("name", ""),
            "source": source,
            "signed_up_at": sub.get("submitted_at", ""),
            "email_sent": sub.get("email_sent", False),
            "email_opened": sub.get("email_opened", False),
            "conversion_completed": sub.get("conversion_completed", False),
            "conversion_at": sub.get("conversion_completed_at"),
            "origin": "form",
        }
        by_source.setdefault(source, []).append(signup)
        all_signups.append(signup)

    # Source 2: 14-day trial signups (trial_14d_signups.json)
    trials_14d = _load_json(TRIAL_14D_FILE, [])
    if isinstance(trials_14d, list):
        for trial in trials_14d:
            source_raw = (trial.get("source") or "").lower()
            campaign_raw = (trial.get("campaign") or "").lower()
            referrer_raw = (trial.get("referer") or "").lower()

            source = _classify_source({
                "source": source_raw,
                "campaign": campaign_raw,
                "referrer": referrer_raw,
            })

            signup = {
                "email": trial.get("email", ""),
                "name": "",
                "source": source,
                "signed_up_at": trial.get("registered_at", ""),
                "email_sent": True,
                "email_opened": False,
                "conversion_completed": False,
                "conversion_at": None,
                "origin": "trial_14d",
                "trial_ends_at": trial.get("trial_ends_at"),
            }
            by_source.setdefault(source, []).append(signup)
            all_signups.append(signup)

    # Build summary
    summary = {}
    for src, signups in by_source.items():
        summary[src] = {
            "count": len(signups),
            "emails_sent": sum(1 for s in signups if s["email_sent"]),
            "emails_opened": sum(1 for s in signups if s["email_opened"]),
            "conversions": sum(1 for s in signups if s["conversion_completed"]),
        }

    return {
        "total": len(all_signups),
        "by_source": summary,
        "signups": all_signups,
    }


def _get_nurturing_metrics() -> dict:
    """Get email nurturing open/click rates by step."""
    state = _load_json(NURTURING_STATE_FILE, {"leads": {}, "metrics": {}})
    clicks_data = _load_json(NURTURING_CLICKS_FILE, {"clicks": []})

    steps = [
        {"id": "welcome", "label": "J+0 Welcome", "day": 0},
        {"id": "day2_case_study", "label": "J+2 Case Study", "day": 2},
        {"id": "day5_expiry_reminder", "label": "J+5 Expiry Reminder", "day": 5},
        {"id": "day7_last_chance", "label": "J+7 Last Chance", "day": 7},
        {"id": "day10_final_offer", "label": "J+10 Final Offer", "day": 10},
    ]

    leads = state.get("leads", {})
    metrics = state.get("metrics", {})
    opens_metrics = metrics.get("opens", {})
    clicks_metrics = metrics.get("clicks", {})

    total_leads = len(leads)

    step_metrics = []
    for step in steps:
        step_id = step["id"]
        opens = opens_metrics.get(step_id, 0)
        clicks = clicks_metrics.get(step_id, 0)

        # Count sends for this step
        sent = 0
        for email, lead in leads.items():
            sent_steps = lead.get("sent_steps", [])
            if step_id in sent_steps or (step_id == "welcome" and lead.get("welcome_sent")):
                sent += 1

        # If no sent data, estimate from total leads (welcome sent to all)
        if sent == 0 and step_id == "welcome":
            sent = total_leads

        open_rate = round((opens / sent * 100) if sent > 0 else 0, 1)
        click_rate = round((clicks / sent * 100) if sent > 0 else 0, 1)

        step_metrics.append({
            "step_id": step_id,
            "label": step["label"],
            "day": step["day"],
            "sent": sent,
            "opens": opens,
            "open_rate": open_rate,
            "clicks": clicks,
            "click_rate": click_rate,
        })

    # CTA clicks detail from clicks file
    cta_clicks = []
    for click in clicks_data.get("clicks", [])[-20:]:
        cta_clicks.append({
            "lead_id": click.get("lead_id", ""),
            "url": click.get("url", ""),
            "timestamp": click.get("timestamp", ""),
        })

    return {
        "total_leads_in_nurturing": total_leads,
        "steps": step_metrics,
        "recent_cta_clicks": cta_clicks,
    }


def _get_conversion_metrics() -> dict:
    """Calculate trial → paid conversion metrics."""
    signups_data = _get_trial_signups_by_source()
    all_signups = signups_data["signups"]

    conversions = [s for s in all_signups if s["conversion_completed"]]
    total = len(all_signups)
    converted = len(conversions)

    # Calculate average time to conversion
    conversion_times = []
    for s in conversions:
        try:
            signup_ts = datetime.fromisoformat(
                s["signed_up_at"].replace("Z", "+00:00"))
            conv_ts = datetime.fromisoformat(
                s["conversion_at"].replace("Z", "+00:00"))
            delta = (conv_ts - signup_ts).total_seconds() / 3600  # hours
            conversion_times.append(delta)
        except (ValueError, TypeError, AttributeError):
            pass

    avg_hours = round(sum(conversion_times) / len(conversion_times), 1) if conversion_times else 0
    avg_days = round(avg_hours / 24, 1)

    return {
        "total_trials": total,
        "total_conversions": converted,
        "conversion_rate": round((converted / total * 100) if total > 0 else 0, 1),
        "avg_time_to_conversion_hours": avg_hours,
        "avg_time_to_conversion_days": avg_days,
        "revenue_generated": 0,  # Will be populated when Stripe is integrated
    }


def _get_funnel_stages() -> list:
    """Build full funnel visualization data."""
    signups_data = _get_trial_signups_by_source()
    nurturing = _get_nurturing_metrics()
    all_signups = signups_data["signups"]

    total_signups = len(all_signups)
    emails_sent = sum(1 for s in all_signups if s["email_sent"])
    emails_opened = sum(1 for s in all_signups if s["email_opened"])

    # Get nurturing engagement (anyone who opened nurturing emails)
    nurturing_engaged = sum(
        step["opens"] for step in nurturing["steps"]
    )

    conversions = sum(1 for s in all_signups if s["conversion_completed"])

    stages = [
        {
            "stage": "Trial Signups",
            "count": total_signups,
            "percentage": 100,
        },
        {
            "stage": "Welcome Email Sent",
            "count": emails_sent,
            "percentage": round((emails_sent / total_signups * 100) if total_signups > 0 else 0, 1),
        },
        {
            "stage": "Email Opened",
            "count": emails_opened,
            "percentage": round((emails_opened / total_signups * 100) if total_signups > 0 else 0, 1),
        },
        {
            "stage": "Nurturing Engaged",
            "count": nurturing_engaged,
            "percentage": round((nurturing_engaged / total_signups * 100) if total_signups > 0 else 0, 1),
        },
        {
            "stage": "Converted to Paid",
            "count": conversions,
            "percentage": round((conversions / total_signups * 100) if total_signups > 0 else 0, 1),
        },
    ]
    return stages


@router.get("/api/conversion-metrics")
async def conversion_metrics():
    """
    Real-time conversion funnel metrics: trial → paid.

    Returns aggregated data for:
    - Trial signups by source (Dev.to, LinkedIn, email, direct)
    - Nurturing email performance by step
    - CTA click tracking
    - Conversion rates and average time to convert
    - Full funnel visualization data
    """
    now = datetime.now(timezone.utc)

    signups = _get_trial_signups_by_source()
    nurturing = _get_nurturing_metrics()
    conversion = _get_conversion_metrics()
    funnel = _get_funnel_stages()

    return {
        "timestamp": now.isoformat(),
        "signups": {
            "total": signups["total"],
            "by_source": signups["by_source"],
        },
        "nurturing": nurturing,
        "conversion": conversion,
        "funnel": funnel,
    }


@router.get("/funnel/dashboard.html")
async def serve_funnel_dashboard():
    """Serve the conversion funnel dashboard HTML page."""
    if os.path.exists(FUNNEL_DASHBOARD_HTML):
        return FileResponse(FUNNEL_DASHBOARD_HTML, media_type="text/html")
    return {"error": "Funnel dashboard HTML not found"}
