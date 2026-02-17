#!/usr/bin/env python3
"""
Monitor conversion signals from page visits
Checks page_visits log every 15min for hot leads (/pricing, /trial visits)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add automation directory to path for imports
sys.path.insert(0, "/opt/claude-ceo/automation")

from email_sender import send_email

LOG_FILE = "/opt/claude-ceo/workspace/arkwatch/logs/page_visits_20260209.json"
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/logs/conversion_monitor_state.json"
ALERT_EMAIL = "apps.desiorac@gmail.com"


def load_visits():
    """Load visits from log file"""
    if not Path(LOG_FILE).exists():
        return []

    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def load_last_check():
    """Load timestamp of last check"""
    if not Path(STATE_FILE).exists():
        return None

    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            return datetime.fromisoformat(state.get("last_check"))
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def save_last_check(timestamp):
    """Save timestamp of current check"""
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({"last_check": timestamp.isoformat()}, f)


def get_hot_signals(visits, since=None):
    """
    Extract hot conversion signals from visits
    Hot signals: /pricing or /trial visits
    """
    hot_signals = []

    for visit in visits:
        visit_time = datetime.fromisoformat(visit["timestamp"])

        # Skip if before last check
        if since and visit_time <= since:
            continue

        # Check if hot signal
        page = visit["page"]
        if page.startswith("/pricing") or page.startswith("/trial"):
            hot_signals.append(visit)

    return hot_signals


def format_alert(signals):
    """Format alert email content"""
    subject = f"🔥 {len(signals)} signal(s) conversion chaud(s) détecté(s)"

    body = f"""
ArkWatch Conversion Monitor - Alerte Temps Réel
===============================================

{len(signals)} visite(s) sur pages à forte conversion détectée(s) :

"""

    for signal in signals:
        body += f"""
---
📍 Page: {signal['page']}
🕐 Date: {signal['timestamp']}
🌐 IP: {signal['ip']}
🖥️  User-Agent: {signal['user_agent'][:80]}...
🔗 Referrer: {signal['referrer']}
📊 Query params: {signal.get('query_params', {})}

"""

    body += """
Action recommandée:
- Vérifier si cet IP correspond à un prospect connu
- Préparer un follow-up personnalisé si lead identifié
- Analyser le comportement (demo → pricing = signal très fort)

Dashboard: https://watch.arkforge.fr/admin/conversion
"""

    return subject, body


def send_alert(signals):
    """Send alert email for hot signals"""
    if not signals:
        return

    subject, body = format_alert(signals)

    try:
        send_email(
            to_email=ALERT_EMAIL,
            subject=subject,
            body=body
        )
        print(f"✅ Alert sent for {len(signals)} hot signal(s)")
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")


def main():
    """Main monitoring loop"""
    print(f"🔍 Checking conversion signals at {datetime.utcnow().isoformat()}")

    # Load visits
    visits = load_visits()
    if not visits:
        print("ℹ️  No visits logged yet")
        save_last_check(datetime.utcnow())
        return

    print(f"📊 Total visits in log: {len(visits)}")

    # Get last check time
    last_check = load_last_check()
    if last_check:
        print(f"⏰ Last check: {last_check.isoformat()}")
    else:
        print("ℹ️  First run - checking last 15 minutes")
        last_check = datetime.utcnow() - timedelta(minutes=15)

    # Find hot signals since last check
    hot_signals = get_hot_signals(visits, since=last_check)

    if hot_signals:
        print(f"🔥 {len(hot_signals)} HOT signal(s) detected!")
        for signal in hot_signals:
            print(f"  - {signal['page']} at {signal['timestamp']}")
        send_alert(hot_signals)
    else:
        print("✅ No new hot signals")

    # Save current check time
    save_last_check(datetime.utcnow())
    print("✅ Monitoring cycle complete")


if __name__ == "__main__":
    main()
