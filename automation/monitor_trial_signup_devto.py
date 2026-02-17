#!/usr/bin/env python3
"""
Real-time monitoring for trial-signup visits post-Dev.to publication.
Runs every 5 minutes via cron. Captures ALL trial-signup visits in the 72h
window after Dev.to article publication, with source attribution.

Sends immediate email alert on each new trial-signup page visit.
Maintains a dashboard JSON file with conversion metrics.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/claude-ceo/automation")

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
LOGS_DIR = Path("/opt/claude-ceo/workspace/arkwatch/logs")
DASHBOARD_FILE = DATA_DIR / "devto_trial_dashboard.json"
STATE_FILE = LOGS_DIR / "devto_trial_monitor_state.json"
ALERT_LOG = LOGS_DIR / "devto_trial_alerts.log"

# Page visits sources
PAGE_VISITS_JSON = LOGS_DIR / "page_visits_20260209.json"
PAGE_VISITS_JSONL = DATA_DIR / "page_visits.jsonl"
SIGNUP_TRACKING = DATA_DIR / "trial_signups_tracking.json"

# Campaign config
DEVTO_PUBLISH_DATE = "2026-02-10T00:00:00+00:00"  # Adjust when article goes live
MONITORING_WINDOW_HOURS = 72
ALERT_EMAIL = "apps.desiorac@gmail.com"

# Alert thresholds
ALERT_ON_EVERY_VISIT = True  # During 72h window, alert on EVERY trial visit
DAILY_SUMMARY_HOUR = 9  # Send daily summary at 9 AM UTC


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(str(tmp), str(path))


def load_state():
    return load_json(STATE_FILE, {
        "last_check": None,
        "processed_visit_keys": [],
        "alerts_sent": 0,
        "last_daily_summary": None
    })


def save_state(state):
    save_json(STATE_FILE, state)


def send_email_alert(subject: str, body: str):
    """Send alert email via email_sender."""
    try:
        from email_sender import send_email
        send_email(to_addr=ALERT_EMAIL, subject=subject, body=body)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


def log_alert(message: str):
    """Append to alert log file."""
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(ALERT_LOG, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def is_within_monitoring_window():
    """Check if we're within 72h of Dev.to publication."""
    now = datetime.now(timezone.utc)
    publish_dt = datetime.fromisoformat(DEVTO_PUBLISH_DATE)
    window_end = publish_dt + timedelta(hours=MONITORING_WINDOW_HOURS)
    return publish_dt <= now <= window_end


def get_all_trial_visits():
    """Collect trial-signup visits from all sources."""
    visits = []

    # Source 1: page_visits JSON (middleware-tracked)
    json_visits = load_json(PAGE_VISITS_JSON, [])
    if isinstance(json_visits, list):
        for v in json_visits:
            page = v.get("page", "")
            if "trial" in page.lower() or "signup" in page.lower():
                visits.append({
                    "timestamp": v.get("timestamp", ""),
                    "page": page,
                    "ip": v.get("ip", "unknown"),
                    "user_agent": v.get("user_agent", "unknown"),
                    "referrer": v.get("referrer", "direct"),
                    "query_params": v.get("query_params", {}),
                    "source_file": "page_visits_json"
                })

    # Source 2: page_visits JSONL (monitor_arkwatch_visits format)
    if PAGE_VISITS_JSONL.exists():
        with open(PAGE_VISITS_JSONL, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    v = json.loads(line)
                    page = v.get("page", "")
                    if "trial" in page.lower() or "signup" in page.lower():
                        visits.append({
                            "timestamp": v.get("timestamp", ""),
                            "page": page,
                            "ip": v.get("ip", "unknown"),
                            "user_agent": v.get("user_agent", "unknown"),
                            "referrer": v.get("referrer", "direct"),
                            "query_params": {},
                            "source_file": "page_visits_jsonl"
                        })
                except json.JSONDecodeError:
                    continue

    # Source 3: trial signup tracking (actual form submissions)
    signup_data = load_json(SIGNUP_TRACKING, {})
    for sub in signup_data.get("submissions", []):
        visits.append({
            "timestamp": sub.get("submitted_at", ""),
            "page": "/trial-signup (form submission)",
            "ip": "form_submission",
            "user_agent": "form",
            "referrer": sub.get("referrer", "direct"),
            "query_params": {
                "utm_source": sub.get("utm_source", ""),
                "utm_campaign": sub.get("utm_campaign", ""),
                "email": sub.get("email", "")
            },
            "source_file": "trial_signups_tracking",
            "is_signup": True,
            "name": sub.get("name", ""),
            "email": sub.get("email", "")
        })

    return visits


def classify_source(visit):
    """Classify traffic source (dev.to vs other)."""
    referrer = (visit.get("referrer") or "").lower()
    utm = (visit.get("query_params", {}).get("utm_source") or "").lower()

    if "dev.to" in referrer or "devto" in utm or "dev_to" in utm:
        return "dev.to"
    elif "linkedin" in referrer or "linkedin" in utm:
        return "linkedin"
    elif "twitter" in referrer or "twitter" in utm or "x.com" in referrer:
        return "twitter"
    elif "google" in referrer or "google" in utm:
        return "google"
    elif "reddit" in referrer or "reddit" in utm:
        return "reddit"
    elif "hackernews" in referrer or "hn" in utm or "news.ycombinator" in referrer:
        return "hackernews"
    elif referrer in ("direct", "", "unknown"):
        return "direct"
    else:
        return "other"


def make_visit_key(visit):
    """Create unique key to deduplicate visits."""
    return f"{visit['timestamp']}_{visit['ip']}_{visit['page']}"


def update_dashboard(all_visits, state):
    """Update the dashboard JSON with current metrics."""
    now = datetime.now(timezone.utc)
    publish_dt = datetime.fromisoformat(DEVTO_PUBLISH_DATE)
    window_end = publish_dt + timedelta(hours=MONITORING_WINDOW_HOURS)

    # Filter visits within monitoring window
    window_visits = []
    for v in all_visits:
        try:
            vt = datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00")) if v["timestamp"] else None
            if vt and publish_dt <= vt <= window_end:
                window_visits.append(v)
        except (ValueError, TypeError):
            continue

    # Source breakdown
    sources = {}
    for v in window_visits:
        src = classify_source(v)
        sources[src] = sources.get(src, 0) + 1

    # Count actual signups
    signups = [v for v in window_visits if v.get("is_signup")]
    total_page_visits = len([v for v in window_visits if not v.get("is_signup")])
    total_signups = len(signups)

    dashboard = {
        "campaign": "devto_trial_monitoring",
        "publish_date": DEVTO_PUBLISH_DATE,
        "monitoring_window_hours": MONITORING_WINDOW_HOURS,
        "window_ends": window_end.isoformat(),
        "is_active": is_within_monitoring_window(),
        "last_updated": now.isoformat(),
        "metrics": {
            "total_trial_page_visits": total_page_visits,
            "total_signups": total_signups,
            "conversion_rate": round(total_signups / total_page_visits * 100, 1) if total_page_visits > 0 else 0.0,
            "sources": sources,
            "devto_visits": sources.get("dev.to", 0),
            "other_visits": total_page_visits - sources.get("dev.to", 0)
        },
        "alerts_sent": state.get("alerts_sent", 0),
        "recent_visits": window_visits[-20:]  # Last 20 visits
    }

    save_json(DASHBOARD_FILE, dashboard)
    return dashboard


def alert_new_visit(visit):
    """Send real-time alert for a new trial-signup visit."""
    source = classify_source(visit)
    is_signup = visit.get("is_signup", False)

    if is_signup:
        subject = f"[SIGNUP] Nouveau trial signup! Source: {source}"
        body = f"""CONVERSION DETECTED - Trial Signup Form Submission
==================================================

Nom: {visit.get('name', 'N/A')}
Email: {visit.get('email', 'N/A')}
Source: {source}
Referrer: {visit.get('referrer', 'direct')}
UTM Source: {visit.get('query_params', {}).get('utm_source', 'N/A')}
UTM Campaign: {visit.get('query_params', {}).get('utm_campaign', 'N/A')}
Timestamp: {visit.get('timestamp', 'N/A')}

ACTION: Follow-up dans les 30 minutes!
"""
    else:
        subject = f"[VISIT] Visite trial-signup - Source: {source}"
        body = f"""Trial Page Visit Detected
=========================

Page: {visit.get('page', 'N/A')}
IP: {visit.get('ip', 'N/A')}
Source: {source}
Referrer: {visit.get('referrer', 'direct')}
User-Agent: {visit.get('user_agent', 'N/A')[:100]}
Query Params: {json.dumps(visit.get('query_params', {}), indent=2)}
Timestamp: {visit.get('timestamp', 'N/A')}

{"FROM DEV.TO - High value lead!" if source == "dev.to" else ""}
Dashboard: /opt/claude-ceo/workspace/arkwatch/data/devto_trial_dashboard.json
"""

    sent = send_email_alert(subject, body)
    log_alert(f"{'SENT' if sent else 'FAILED'}: {subject}")
    return sent


def main():
    now = datetime.now(timezone.utc)
    print(f"[{now.isoformat()}] Dev.to Trial Signup Monitor - Starting")

    state = load_state()
    last_check = state.get("last_check")

    # Collect all trial visits
    all_visits = get_all_trial_visits()
    print(f"Total trial-related visits found: {len(all_visits)}")

    # Find new visits since last check
    processed_keys = set(state.get("processed_visit_keys", []))
    new_visits = []

    for visit in all_visits:
        key = make_visit_key(visit)
        if key not in processed_keys:
            new_visits.append(visit)
            processed_keys.add(key)

    print(f"New visits since last check: {len(new_visits)}")

    # Send alerts for new visits (during monitoring window or always for signups)
    alerts_sent = 0
    in_window = is_within_monitoring_window()

    for visit in new_visits:
        is_signup = visit.get("is_signup", False)
        # Alert on signups always, page visits only during 72h window
        if is_signup or (in_window and ALERT_ON_EVERY_VISIT):
            if alert_new_visit(visit):
                alerts_sent += 1

    if alerts_sent > 0:
        print(f"Alerts sent: {alerts_sent}")

    # Update dashboard
    dashboard = update_dashboard(all_visits, state)
    print(f"Dashboard updated: {dashboard['metrics']['total_trial_page_visits']} visits, "
          f"{dashboard['metrics']['total_signups']} signups, "
          f"{dashboard['metrics']['conversion_rate']}% conversion")
    print(f"Sources: {json.dumps(dashboard['metrics']['sources'])}")

    # Save state
    state["last_check"] = now.isoformat()
    state["processed_visit_keys"] = list(processed_keys)[-5000:]  # Keep last 5000 keys
    state["alerts_sent"] = state.get("alerts_sent", 0) + alerts_sent
    save_state(state)

    print(f"[{now.isoformat()}] Monitor complete. Window active: {in_window}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
