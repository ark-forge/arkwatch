"""Conversion Dashboard Router - Real-time tracking of 35 leads with alerting

Tracks leads from:
- Direct outreach campaign (15 DevOps/SRE leaders)
- HN outreach campaign (20 HN-sourced leads)
- Trial signups (form submissions)
- Page visits (high-value pages: /pricing, /demo, /trial-signup)

Smart behavioral alerts:
- Pricing visit + no signup within 10min
- Demo click + no form submission
- Email open + site visit within 1h
- High engagement (3+ opens, no trial)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import glob as glob_module

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Email sender for alerts
sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

router = APIRouter()

# Data source paths
OUTREACH_TRACKING = "/opt/claude-ceo/workspace/arkwatch/data/outreach_email_tracking_20260209.json"
HN_OUTREACH_DIR = "/opt/claude-ceo/workspace/croissance"
TRIAL_SIGNUPS = "/opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json"
PAGE_VISITS = "/opt/claude-ceo/workspace/arkwatch/data/page_visits.jsonl"
HOT_LEADS_FILE = "/opt/claude-ceo/workspace/croissance/hot_leads_detected.json"
LEADGEN_ANALYTICS = "/opt/claude-ceo/workspace/arkwatch/data/leadgen_analytics.json"
DEMO_LEADS = "/opt/claude-ceo/workspace/arkwatch/data/demo_leads.json"
ALERT_STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/data/conversion_alert_state.json"

# Alert config
SHAREHOLDER_EMAIL = "apps.desiorac@gmail.com"
ALERT_COOLDOWN_MINUTES = 30  # Don't re-alert for same event type within 30min
PRICING_NO_SIGNUP_WINDOW_MIN = 10  # Alert if pricing visit + no signup within 10min
DEMO_NO_FORM_WINDOW_MIN = 10  # Alert if demo click + no form submission within 10min
EMAIL_OPEN_SITE_VISIT_WINDOW_H = 1  # Alert if email open + site visit within 1h


def _load_json(path: str, default=None):
    """Safely load a JSON file."""
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return default


def _load_jsonl(path: str) -> list:
    """Load a JSONL file as list of dicts."""
    entries = []
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
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


def _load_alert_state() -> dict:
    """Load alert state to track cooldowns."""
    return _load_json(ALERT_STATE_FILE, {"alerts_sent": [], "last_check": None})


def _save_alert_state(state: dict):
    """Save alert state."""
    path = Path(ALERT_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(path)


def _get_outreach_metrics() -> dict:
    """Extract metrics from outreach email tracking."""
    data = _load_json(OUTREACH_TRACKING, {"leads": [], "metrics": {}})
    leads = data.get("leads", [])
    metrics = data.get("metrics", {})

    # Build lead details
    lead_details = []
    for lead in leads:
        if not lead.get("lead_name"):
            continue  # Skip test/unknown leads (id 999, 777, etc.)
        opens = lead.get("opens", [])
        lead_details.append({
            "id": lead.get("id"),
            "name": lead.get("lead_name", "Unknown"),
            "company": lead.get("company", "Unknown"),
            "title": lead.get("title", ""),
            "email": lead.get("email", ""),
            "status": lead.get("status", "unknown"),
            "opened": lead.get("opened") is not None,
            "first_open": lead.get("opened"),
            "open_count": len(opens),
            "last_open": opens[-1] if opens else None,
            "replied": lead.get("replied") is not None,
            "trial_activated": lead.get("trial_activated") is not None,
        })

    total = len(lead_details)
    opened = sum(1 for l in lead_details if l["opened"])
    replied = sum(1 for l in lead_details if l["replied"])
    trials = sum(1 for l in lead_details if l["trial_activated"])

    return {
        "total_leads": total,
        "opened": opened,
        "open_rate": round((opened / total * 100) if total > 0 else 0, 1),
        "replied": replied,
        "reply_rate": round((replied / total * 100) if total > 0 else 0, 1),
        "trials_activated": trials,
        "leads": lead_details,
    }


def _get_hn_outreach_metrics() -> dict:
    """Extract metrics from HN outreach campaigns."""
    # Find the most recent HN campaign file
    hn_files = sorted(glob_module.glob(os.path.join(HN_OUTREACH_DIR, "hn_outreach_campaign*_20260964.json")))
    if not hn_files:
        hn_files = sorted(glob_module.glob(os.path.join(HN_OUTREACH_DIR, "hn_outreach_campaign*.json")))

    lead_details = []
    for hn_file in hn_files[-1:]:  # Use most recent campaign
        data = _load_json(hn_file, {"emails": []})
        emails = data.get("emails", [])
        for em in emails:
            lead_details.append({
                "id": em.get("tracking_id", ""),
                "name": em.get("name", "Unknown"),
                "company": em.get("company", "Unknown"),
                "title": em.get("role", ""),
                "email": em.get("email", ""),
                "source": "hackernews",
                "pain_point": em.get("pain_point", ""),
                "status": em.get("status", "scheduled"),
                "opened": em.get("opened") is not None if "opened" in em else False,
                "open_count": em.get("opens_count", 0),
                "replied": em.get("replied") is not None if "replied" in em else False,
                "trial_activated": em.get("trial_activated") is not None if "trial_activated" in em else False,
            })

    total = len(lead_details)
    opened = sum(1 for l in lead_details if l["opened"])
    replied = sum(1 for l in lead_details if l["replied"])

    return {
        "total_leads": total,
        "opened": opened,
        "open_rate": round((opened / total * 100) if total > 0 else 0, 1),
        "replied": replied,
        "leads": lead_details,
    }


def _get_trial_signup_metrics() -> dict:
    """Extract metrics from trial signups."""
    data = _load_json(TRIAL_SIGNUPS, {"submissions": [], "metrics": {}})
    submissions = data.get("submissions", [])

    signup_details = []
    for sub in submissions:
        signup_details.append({
            "submission_id": sub.get("submission_id", ""),
            "name": sub.get("name", "Unknown"),
            "email": sub.get("email", ""),
            "usecase": sub.get("usecase", ""),
            "source": sub.get("source", "direct"),
            "utm_source": sub.get("utm_source"),
            "submitted_at": sub.get("submitted_at"),
            "email_sent": sub.get("email_sent", False),
            "email_opened": sub.get("email_opened", False),
            "conversion_completed": sub.get("conversion_completed", False),
        })

    total = len(signup_details)
    emails_sent = sum(1 for s in signup_details if s["email_sent"])
    emails_opened = sum(1 for s in signup_details if s["email_opened"])
    conversions = sum(1 for s in signup_details if s["conversion_completed"])

    return {
        "total_signups": total,
        "emails_sent": emails_sent,
        "emails_opened": emails_opened,
        "conversions": conversions,
        "conversion_rate": round((conversions / total * 100) if total > 0 else 0, 1),
        "signups": signup_details,
    }


def _get_page_visit_metrics() -> dict:
    """Extract metrics from page visits."""
    visits = _load_jsonl(PAGE_VISITS)

    by_page = {}
    recent_visits = []
    now = datetime.now(timezone.utc)

    for v in visits:
        page = v.get("page", "unknown")
        by_page[page] = by_page.get(page, 0) + 1

        # Track recent visits (last 24h)
        ts_str = v.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if now - ts < timedelta(hours=24):
                recent_visits.append({
                    "page": page,
                    "timestamp": ts_str,
                    "ip": v.get("ip", "unknown"),
                    "referrer": v.get("referrer", ""),
                    "utm_source": v.get("utm_source", ""),
                })
        except (ValueError, TypeError):
            pass

    return {
        "total_visits": len(visits),
        "by_page": by_page,
        "recent_24h": len(recent_visits),
        "recent_visits": recent_visits,
    }


def _get_demo_leads_metrics() -> dict:
    """Extract metrics from demo leads."""
    data = _load_json(DEMO_LEADS, [])
    if isinstance(data, list):
        leads = data
    else:
        leads = data.get("leads", [])

    return {
        "total_demo_leads": len(leads),
        "leads": leads[:20],  # Last 20
    }


def _detect_hot_leads(outreach: dict, signups: dict, visits: dict,
                      hn_outreach: dict = None) -> list:
    """Detect hot leads requiring immediate attention.

    Smart behavioral triggers:
    1. High engagement: 3+ email opens, no trial
    2. Pricing visit + no signup within 10min window
    3. Demo visit + no form submission within 10min
    4. Email open + site visit within 1h (cross-channel correlation)
    5. Trial stalled: opened email but not converted
    """
    hot_leads = []
    now = datetime.now(timezone.utc)

    # 1. Outreach leads who opened email multiple times (engaged) - direct + HN
    all_outreach_leads = list(outreach.get("leads", []))
    if hn_outreach:
        all_outreach_leads.extend(hn_outreach.get("leads", []))

    for lead in all_outreach_leads:
        if lead.get("open_count", 0) >= 3 and not lead.get("trial_activated"):
            hot_leads.append({
                "type": "high_engagement",
                "severity": "high",
                "lead_name": lead.get("name", "Unknown"),
                "company": lead.get("company", "Unknown"),
                "detail": f"Opened email {lead.get('open_count', 0)}x - highly engaged, no trial yet",
                "action": "Send personalized follow-up or call",
                "email": lead.get("email", ""),
            })

    # 2. Pricing visit + no signup within window (CRITICAL: react <5min)
    recent_visits = visits.get("recent_visits", [])
    pricing_visits_recent = []
    for v in recent_visits:
        if v["page"] in ("/pricing", "/pricing-v2", "/pricing.html"):
            try:
                ts = datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00"))
                if now - ts < timedelta(minutes=PRICING_NO_SIGNUP_WINDOW_MIN):
                    pricing_visits_recent.append(v)
            except (ValueError, TypeError):
                pass

    if pricing_visits_recent:
        # Check if any signup happened in the same window
        recent_signups = []
        for s in signups.get("signups", []):
            try:
                sub_ts = datetime.fromisoformat(
                    s.get("submitted_at", "").replace("Z", "+00:00"))
                if now - sub_ts < timedelta(minutes=PRICING_NO_SIGNUP_WINDOW_MIN):
                    recent_signups.append(s)
            except (ValueError, TypeError):
                pass

        if not recent_signups:
            unique_ips = set(v.get("ip", "") for v in pricing_visits_recent)
            hot_leads.append({
                "type": "pricing_no_signup",
                "severity": "high",
                "lead_name": f"Visitor(s) from {len(unique_ips)} IP(s)",
                "company": "Unknown",
                "detail": f"{len(pricing_visits_recent)} pricing visits in last {PRICING_NO_SIGNUP_WINDOW_MIN}min, 0 signups - potential drop-off",
                "action": "Check pricing page now, visitor may still be browsing",
            })

    # 3. Demo visit + no form submission within window
    demo_visits_recent = []
    for v in recent_visits:
        if v["page"] in ("/demo", "/demo.html"):
            try:
                ts = datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00"))
                if now - ts < timedelta(minutes=DEMO_NO_FORM_WINDOW_MIN):
                    demo_visits_recent.append(v)
            except (ValueError, TypeError):
                pass

    if demo_visits_recent:
        demo_data = _load_json(DEMO_LEADS, {"leads": []})
        demo_leads_list = demo_data if isinstance(demo_data, list) else demo_data.get("leads", [])
        recent_demos = []
        for d in demo_leads_list:
            try:
                dt = datetime.fromisoformat(
                    d.get("submitted_at", d.get("timestamp", "")).replace("Z", "+00:00"))
                if now - dt < timedelta(minutes=DEMO_NO_FORM_WINDOW_MIN):
                    recent_demos.append(d)
            except (ValueError, TypeError):
                pass

        if not recent_demos:
            hot_leads.append({
                "type": "demo_no_form",
                "severity": "high",
                "lead_name": "Demo page visitor",
                "company": "Unknown",
                "detail": f"{len(demo_visits_recent)} demo page visits in last {DEMO_NO_FORM_WINDOW_MIN}min, no demo request submitted",
                "action": "Demo page visitor may need help - check for UX issues",
            })

    # 4. Email open + site visit within 1h (cross-channel correlation = high intent)
    email_opens_1h = []
    for lead in all_outreach_leads:
        last_open = lead.get("last_open") or lead.get("first_open")
        if last_open:
            try:
                open_ts = datetime.fromisoformat(last_open.replace("Z", "+00:00"))
                if now - open_ts < timedelta(hours=EMAIL_OPEN_SITE_VISIT_WINDOW_H):
                    email_opens_1h.append(lead)
            except (ValueError, TypeError):
                pass

    site_visits_1h = []
    for v in recent_visits:
        try:
            ts = datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00"))
            if now - ts < timedelta(hours=EMAIL_OPEN_SITE_VISIT_WINDOW_H):
                site_visits_1h.append(v)
        except (ValueError, TypeError):
            pass

    if email_opens_1h and site_visits_1h:
        for lead in email_opens_1h:
            if not lead.get("trial_activated"):
                hot_leads.append({
                    "type": "email_then_visit",
                    "severity": "high",
                    "lead_name": lead.get("name", "Unknown"),
                    "company": lead.get("company", "Unknown"),
                    "detail": f"Opened email + visited site within 1h - very high intent signal",
                    "action": "Send immediate personalized follow-up, offer live demo",
                    "email": lead.get("email", ""),
                })
                break  # One alert is enough to trigger action

    # 5. Trial signups who haven't converted
    for signup in signups.get("signups", []):
        if signup["email_opened"] and not signup["conversion_completed"]:
            hot_leads.append({
                "type": "trial_stalled",
                "severity": "medium",
                "lead_name": signup["name"],
                "company": "",
                "detail": f"Opened trial email but hasn't converted - usecase: {signup.get('usecase', 'N/A')[:60]}",
                "action": "Send follow-up email with onboarding help",
                "email": signup.get("email", ""),
            })

    # Deduplicate by lead email (keep highest severity)
    seen_emails = set()
    deduped = []
    severity_order = {"high": 0, "medium": 1, "low": 2}
    hot_leads.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))
    for hl in hot_leads:
        email = hl.get("email", "")
        key = email if email else hl.get("lead_name", "") + hl.get("type", "")
        if key not in seen_emails:
            seen_emails.add(key)
            deduped.append(hl)

    return deduped


def _check_and_send_alerts(hot_leads: list, outreach: dict, visits: dict) -> list:
    """Check for critical events and send alerts if needed."""
    alerts_triggered = []
    state = _load_alert_state()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Clean old alerts (older than cooldown)
    cutoff = (now - timedelta(minutes=ALERT_COOLDOWN_MINUTES)).isoformat()
    state["alerts_sent"] = [
        a for a in state.get("alerts_sent", [])
        if a.get("timestamp", "") > cutoff
    ]

    # Check what alert types were recently sent
    recent_types = {a.get("type") for a in state.get("alerts_sent", [])}

    for lead in hot_leads:
        if lead["severity"] == "high" and lead["type"] not in recent_types:
            alert = {
                "type": lead["type"],
                "timestamp": now_iso,
                "lead": lead.get("lead_name", "Unknown"),
                "detail": lead["detail"],
            }

            # Send email alert
            if EMAIL_AVAILABLE:
                try:
                    subject = f"[ArkWatch HOT LEAD] {lead.get('lead_name', 'Unknown')} - {lead['company']}"
                    body = f"""
<h2>Hot Lead Alert</h2>
<p><strong>Lead:</strong> {lead.get('lead_name', 'Unknown')} ({lead.get('company', '')})</p>
<p><strong>Type:</strong> {lead['type']}</p>
<p><strong>Detail:</strong> {lead['detail']}</p>
<p><strong>Recommended Action:</strong> {lead['action']}</p>
<p><strong>Email:</strong> {lead.get('email', 'N/A')}</p>
<hr>
<p><a href="https://watch.arkforge.fr/conversion/dashboard.html">View Dashboard</a></p>
"""
                    send_email(
                        to_addr=SHAREHOLDER_EMAIL,
                        subject=subject,
                        body="Hot lead alert",
                        html_body=body,
                    )
                    alert["email_sent"] = True
                except Exception as e:
                    alert["email_sent"] = False
                    alert["error"] = str(e)
            else:
                alert["email_sent"] = False
                alert["note"] = "Email not available"

            state["alerts_sent"].append(alert)
            alerts_triggered.append(alert)

    state["last_check"] = now_iso
    _save_alert_state(state)

    return alerts_triggered


@router.get("/api/conversion/dashboard")
async def conversion_dashboard(
    include_leads: bool = Query(True, description="Include individual lead details"),
    check_alerts: bool = Query(True, description="Check and trigger alerts for hot leads"),
):
    """
    Real-time conversion dashboard aggregating all tracking data.

    Tracks 35 leads across:
    - Direct outreach campaign (15 DevOps/SRE leaders)
    - HN outreach campaign (20 HN-sourced leads)
    - Trial signups (form submissions)
    - Page visits (high-value pages)
    - Demo leads
    - Hot lead detection + behavioral alerts
    """
    now = datetime.now(timezone.utc)

    # Gather all metrics
    outreach = _get_outreach_metrics()
    hn_outreach = _get_hn_outreach_metrics()
    signups = _get_trial_signup_metrics()
    visits = _get_page_visit_metrics()
    demo = _get_demo_leads_metrics()

    # Detect hot leads with all sources
    hot_leads = _detect_hot_leads(outreach, signups, visits, hn_outreach)

    # Check alerts
    alerts = []
    if check_alerts:
        alerts = _check_and_send_alerts(hot_leads, outreach, visits)

    total_outreach = outreach["total_leads"] + hn_outreach["total_leads"]
    total_opens = outreach["opened"] + hn_outreach["opened"] + signups["emails_opened"]

    # Build response
    response = {
        "timestamp": now.isoformat(),
        "summary": {
            "total_leads_tracked": total_outreach + signups["total_signups"],
            "total_email_opens": total_opens,
            "total_page_visits": visits["total_visits"],
            "total_signups": signups["total_signups"],
            "total_conversions": signups["conversions"],
            "total_demo_leads": demo["total_demo_leads"],
            "hot_leads_count": len(hot_leads),
            "alerts_triggered": len(alerts),
        },
        "outreach_campaign": {
            "total_leads": outreach["total_leads"],
            "opened": outreach["opened"],
            "open_rate": outreach["open_rate"],
            "replied": outreach["replied"],
            "reply_rate": outreach["reply_rate"],
            "trials_activated": outreach["trials_activated"],
        },
        "hn_outreach_campaign": {
            "total_leads": hn_outreach["total_leads"],
            "opened": hn_outreach["opened"],
            "open_rate": hn_outreach["open_rate"],
            "replied": hn_outreach["replied"],
        },
        "trial_signups": {
            "total": signups["total_signups"],
            "emails_sent": signups["emails_sent"],
            "emails_opened": signups["emails_opened"],
            "conversions": signups["conversions"],
            "conversion_rate": signups["conversion_rate"],
        },
        "page_visits": {
            "total": visits["total_visits"],
            "by_page": visits["by_page"],
            "recent_24h": visits["recent_24h"],
        },
        "hot_leads": hot_leads,
        "alerts": alerts,
    }

    # Include details if requested
    if include_leads:
        response["outreach_campaign"]["leads"] = outreach["leads"]
        response["hn_outreach_campaign"]["leads"] = hn_outreach["leads"]
        response["trial_signups"]["signups"] = signups["signups"]
        response["page_visits"]["recent_visits"] = visits["recent_visits"]

    return response


@router.get("/api/conversion/hot-leads")
async def get_hot_leads():
    """Get only hot leads requiring immediate action."""
    outreach = _get_outreach_metrics()
    hn_outreach = _get_hn_outreach_metrics()
    signups = _get_trial_signup_metrics()
    visits = _get_page_visit_metrics()

    hot_leads = _detect_hot_leads(outreach, signups, visits, hn_outreach)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hot_leads_count": len(hot_leads),
        "hot_leads": hot_leads,
    }


@router.post("/api/conversion/test-alert")
async def test_alert():
    """Send a test alert to verify alerting pipeline works."""
    now = datetime.now(timezone.utc)

    test_alert = {
        "type": "test_alert",
        "timestamp": now.isoformat(),
        "lead": "Test Lead",
        "detail": "This is a test alert from the conversion dashboard",
    }

    if EMAIL_AVAILABLE:
        try:
            send_email(
                to_addr=SHAREHOLDER_EMAIL,
                subject="[ArkWatch TEST] Conversion Dashboard Alert Test",
                body="Test alert from conversion dashboard",
                html_body=f"""
<h2>Test Alert - Conversion Dashboard</h2>
<p>This is a test alert from the ArkWatch conversion dashboard.</p>
<p><strong>Timestamp:</strong> {now.isoformat()}</p>
<p>If you received this, the alerting pipeline is working correctly.</p>
<hr>
<p><a href="https://watch.arkforge.fr/conversion/dashboard.html">View Dashboard</a></p>
""",
            )
            test_alert["email_sent"] = True
            test_alert["recipient"] = SHAREHOLDER_EMAIL
        except Exception as e:
            test_alert["email_sent"] = False
            test_alert["error"] = str(e)
    else:
        test_alert["email_sent"] = False
        test_alert["note"] = "Email module not available"

    # Log the test alert
    state = _load_alert_state()
    state["alerts_sent"].append(test_alert)
    state["last_check"] = now.isoformat()
    _save_alert_state(state)

    return test_alert


DASHBOARD_HTML = "/opt/claude-ceo/workspace/arkwatch/site/conversion-dashboard.html"


@router.get("/conversion/dashboard.html")
async def serve_dashboard():
    """Serve the conversion dashboard HTML page."""
    if os.path.exists(DASHBOARD_HTML):
        return FileResponse(DASHBOARD_HTML, media_type="text/html")
    return {"error": "Dashboard HTML not found"}
