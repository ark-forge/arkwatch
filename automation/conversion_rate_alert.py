#!/usr/bin/env python3
"""Conversion Rate Alert System for ArkWatch Trials"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
TRIAL_SIGNUPS_FILE = DATA_DIR / "trial_14d_signups.json"
TRIAL_ACTIVITY_FILE = DATA_DIR / "trial_activity.json"
ALERT_STATE_FILE = DATA_DIR / "conversion_alerts_state.json"
TRIAL_END_WARNING_DAYS = 2


def load_json(file_path: Path):
    if not file_path.exists():
        return [] if "signups" in str(file_path) else {}
    try:
        with open(file_path) as f:
            data = json.load(f)
            if file_path.name == "trial_activity.json" and isinstance(data, list):
                return {"trials": {}, "last_check": None}
            return data
    except:
        return [] if "signups" in str(file_path) else {}


def save_json(file_path: Path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(file_path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    import os
    os.replace(tmp, str(file_path))


def send_alert(subject: str, body: str):
    try:
        subprocess.run([
            "python3", "/opt/claude-ceo/automation/email_sender.py",
            "apps.desiorac@gmail.com", subject, body
        ], timeout=15, check=False, capture_output=True)
    except:
        pass


def check_expiring_trials():
    signups = load_json(TRIAL_SIGNUPS_FILE)
    activity = load_json(TRIAL_ACTIVITY_FILE)
    alert_state = load_json(ALERT_STATE_FILE)
    
    trials_data = activity.get("trials", {})
    expiring_alerts = alert_state.get("expiring_trial_alerts", {})
    now = datetime.now(timezone.utc)
    alerts_sent = []

    for signup in signups:
        email = signup["email"]
        trial_ends = signup.get("trial_ends_at")
        if not trial_ends:
            continue

        try:
            trial_end_dt = datetime.fromisoformat(trial_ends.replace("Z", "+00:00"))
        except:
            continue
            
        days_remaining = (trial_end_dt - now).days

        if 0 <= days_remaining <= TRIAL_END_WARNING_DAYS:
            is_activated = trials_data.get(email, {}).get("activated", False)
            if not is_activated and email not in expiring_alerts:
                send_alert(f"⚠️ TRIAL EXPIRING: {email}", 
                          f"Trial expire dans {days_remaining}j sans activation")
                alerts_sent.append(email)
                expiring_alerts[email] = trial_ends

    if alerts_sent:
        alert_state["expiring_trial_alerts"] = expiring_alerts
        save_json(ALERT_STATE_FILE, alert_state)
    return alerts_sent


def generate_report():
    signups = load_json(TRIAL_SIGNUPS_FILE)
    activity = load_json(TRIAL_ACTIVITY_FILE)
    trials_data = activity.get("trials", {})

    total = len(signups)
    activated = sum(1 for t in trials_data.values() if t.get("activated"))
    converted = sum(1 for t in trials_data.values() if t.get("converted"))

    return {
        "signups": total,
        "activated": activated,
        "converted": converted,
        "activation_rate": round(activated / total * 100, 1) if total > 0 else 0,
        "conversion_rate": round(converted / activated * 100, 1) if activated > 0 else 0
    }


def main():
    print("🔍 ArkWatch Conversion Monitoring")
    print("=" * 50)
    
    alerts = check_expiring_trials()
    print(f"\n📅 Expiring trials: {len(alerts)} alerts sent" if alerts else "\n📅 No expiring trials")
    
    report = generate_report()
    print(f"\n📈 Report:")
    print(f"   Signups: {report['signups']}")
    print(f"   Activated: {report['activated']} ({report['activation_rate']}%)")
    print(f"   Converted: {report['converted']} ({report['conversion_rate']}%)")
    print("\n" + "=" * 50 + "\n✓ Complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
