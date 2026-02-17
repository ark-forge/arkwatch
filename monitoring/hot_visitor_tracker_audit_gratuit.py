#!/usr/bin/env python3
"""
MONITORING TEMPS RÉEL - Visiteurs HOT page /audit-gratuit-monitoring.html
Détecte visiteurs à forte intention (durée > 2min OU scroll > 70%) et envoie SMS shareholder.

FONDATIONS TASK #87 - 2026-02-10
Basé sur hot_visitor_tracker_trial14d.py
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add automation for OVH SMS
sys.path.insert(0, "/opt/claude-ceo/automation")

# Configuration
SHAREHOLDER_PHONE = "+33749879812"

# Critères HOT visitor - page audit gratuit
HOT_CRITERIA = {
    "time_on_page_min": 120,  # 2 minutes = 120 secondes
    "scroll_depth_min": 70,   # 70% scroll
}

# Window d'opportunité chaude
HOT_WINDOW_MINUTES = 5  # 5 minutes pour relance manuelle

# Paths
VISITOR_LOG = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_visitors.jsonl"
HOT_ALERTS_LOG = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_hot_alerts.jsonl"
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/monitoring/audit_gratuit_hot_state.json"
OVH_CREDENTIALS = "/opt/claude-ceo/config/ovh_credentials.json"

# Cooldown: 1 SMS par visiteur par 24h
ALERT_COOLDOWN_HOURS = 24


class AuditGratuitHotTracker:
    """Track visitors on /audit-gratuit-monitoring.html and detect HOT leads"""

    def __init__(self):
        self.state = self.load_state()
        self.visitors = defaultdict(lambda: {
            "first_seen": None,
            "last_seen": None,
            "interactions": 0,
            "time_on_page": 0,
            "scroll_depth": 0,
            "form_started": False,
            "form_submitted": False,
            "is_hot": False,
            "alert_sent": False,
            "alert_sent_at": None,
            "ip": None,
            "referrer": None,
            "user_agent": None,
            "device": None,
        })
        self.hot_detected = []
        self.ovh_client = None

    def load_state(self) -> Dict:
        """Load monitoring state"""
        if Path(STATE_FILE).exists():
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        return {
            "total_visitors": 0,
            "total_hot_detected": 0,
            "total_sms_sent": 0,
            "last_check": None,
            "alerts_sent_24h": 0,
        }

    def save_state(self):
        """Save monitoring state"""
        self.state["last_check"] = datetime.now(timezone.utc).isoformat()
        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(STATE_FILE).with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        tmp.replace(STATE_FILE)

    def init_ovh_client(self):
        """Initialize OVH SMS client"""
        if not Path(OVH_CREDENTIALS).exists():
            print(f"WARNING: OVH credentials not found at {OVH_CREDENTIALS}")
            return False

        try:
            import ovh

            with open(OVH_CREDENTIALS) as f:
                creds = json.load(f)

            self.ovh_client = ovh.Client(
                endpoint=creds["endpoint"],
                application_key=creds["application_key"],
                application_secret=creds["application_secret"],
                consumer_key=creds["consumer_key"],
            )

            services = self.ovh_client.get('/sms')
            if not services:
                print("WARNING: No SMS services found in OVH account")
                return False

            print(f"OVH SMS client initialized - {len(services)} service(s)")
            return True

        except ImportError:
            print("ERROR: ovh library not installed - run: pip3 install ovh")
            return False
        except Exception as e:
            print(f"ERROR initializing OVH client: {e}")
            return False

    def detect_device(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        ua = (user_agent or "").lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            return "mobile"
        if "tablet" in ua or "ipad" in ua:
            return "tablet"
        return "desktop"

    def send_sms_alert(self, visitor_id: str, visitor_data: Dict) -> bool:
        """Send SMS alert to shareholder via OVH"""
        if not self.ovh_client:
            print("WARNING: OVH client not initialized - alert logged only")
            return False

        # Check cooldown
        if visitor_data.get("alert_sent_at"):
            last_alert = datetime.fromisoformat(visitor_data["alert_sent_at"])
            if (datetime.now(timezone.utc) - last_alert).total_seconds() < ALERT_COOLDOWN_HOURS * 3600:
                print(f"Cooldown active for {visitor_id} - SMS skipped")
                return False

        try:
            services = self.ovh_client.get('/sms')
            if not services:
                print("ERROR: No SMS service available")
                return False

            service_name = services[0]

            time_min = visitor_data.get("time_on_page", 0) // 60
            time_sec = visitor_data.get("time_on_page", 0) % 60
            scroll = visitor_data.get("scroll_depth", 0)
            ip = visitor_data.get("ip", "?")
            referrer = visitor_data.get("referrer", "direct")
            device = visitor_data.get("device", "?")

            message = (
                f"HOT LEAD /audit-gratuit\n"
                f"Temps: {time_min}m{time_sec:02d}s | Scroll: {scroll}%\n"
                f"IP: {ip}\n"
                f"Ref: {referrer[:30]}\n"
                f"Device: {device}\n"
                f"RELANCE dans 5min!"
            )

            result = self.ovh_client.post(
                f'/sms/{service_name}/jobs',
                charset='UTF-8',
                message=message,
                receivers=[SHAREHOLDER_PHONE],
                sender='ArkWatch',
                priority='high',
            )

            print(f"SMS sent via OVH - {result.get('totalCreditsRemoved', 0)} credits")
            self.state["total_sms_sent"] += 1
            return True

        except Exception as e:
            print(f"ERROR sending SMS: {e}")
            return False

    def log_hot_alert(self, visitor_id: str, visitor_data: Dict, sms_sent: bool):
        """Log HOT visitor alert to JSONL"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "visitor_id": visitor_id,
            "time_on_page": visitor_data.get("time_on_page", 0),
            "scroll_depth": visitor_data.get("scroll_depth", 0),
            "ip": visitor_data.get("ip"),
            "referrer": visitor_data.get("referrer"),
            "device": visitor_data.get("device"),
            "user_agent": visitor_data.get("user_agent"),
            "form_started": visitor_data.get("form_started", False),
            "form_submitted": visitor_data.get("form_submitted", False),
            "sms_sent": sms_sent,
            "hot_window_expires": (
                datetime.now(timezone.utc) + timedelta(minutes=HOT_WINDOW_MINUTES)
            ).isoformat(),
        }

        Path(HOT_ALERTS_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(HOT_ALERTS_LOG, "a") as f:
            f.write(json.dumps(alert) + "\n")

        self.hot_detected.append(alert)

    def analyze_visitor(self, visitor_id: str, events: List[Dict]) -> Dict:
        """Analyze visitor behavior from event stream"""
        visitor = self.visitors[visitor_id]

        for event in events:
            event_type = event.get("type")
            timestamp = event.get("timestamp")

            if not visitor["first_seen"]:
                visitor["first_seen"] = timestamp

            visitor["last_seen"] = timestamp

            # Capture profile info from first event
            if not visitor["ip"]:
                visitor["ip"] = event.get("ip", "unknown")
                visitor["referrer"] = event.get("referer", event.get("referrer", "direct"))
                visitor["user_agent"] = event.get("user_agent", "")
                visitor["device"] = self.detect_device(visitor["user_agent"])

            # Count interactions
            if event_type in ["click", "scroll", "form_focus", "form_input"]:
                visitor["interactions"] += 1

            # Track scroll depth
            if event_type == "scroll":
                visitor["scroll_depth"] = max(
                    visitor["scroll_depth"],
                    event.get("depth", event.get("scroll_depth", 0))
                )

            # Track form interaction
            if event_type in ["form_focus", "form_input"]:
                visitor["form_started"] = True

            if event_type == "form_submit":
                visitor["form_submitted"] = True

            # Track time from heartbeat events
            if event_type == "heartbeat" and event.get("time_on_page"):
                visitor["time_on_page"] = max(
                    visitor["time_on_page"],
                    event["time_on_page"]
                )

        # Calculate time from timestamps if heartbeat not available
        if visitor["first_seen"] and visitor["last_seen"] and visitor["time_on_page"] == 0:
            try:
                first = datetime.fromisoformat(visitor["first_seen"])
                last = datetime.fromisoformat(visitor["last_seen"])
                visitor["time_on_page"] = int((last - first).total_seconds())
            except (ValueError, TypeError):
                pass

        return visitor

    def is_hot_visitor(self, visitor_data: Dict) -> bool:
        """Determine if visitor is HOT: time > 2min OR scroll > 70%"""
        # Already submitted form = converted, no need for alert
        if visitor_data.get("form_submitted"):
            return False

        # Criterion 1: Time on page > 2 minutes
        if visitor_data["time_on_page"] >= HOT_CRITERIA["time_on_page_min"]:
            return True

        # Criterion 2: Scroll depth > 70%
        if visitor_data["scroll_depth"] >= HOT_CRITERIA["scroll_depth_min"]:
            return True

        return False

    def load_visitor_events(self) -> Dict[str, List[Dict]]:
        """Load visitor events from JSONL log"""
        events_by_visitor = defaultdict(list)

        if not Path(VISITOR_LOG).exists():
            return events_by_visitor

        try:
            with open(VISITOR_LOG) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    visitor_id = event.get("visitor_id") or event.get("ip", "unknown")
                    events_by_visitor[visitor_id].append(event)
        except Exception as e:
            print(f"ERROR loading visitor events: {e}")

        return events_by_visitor

    def monitor_cycle(self) -> Dict:
        """Run one monitoring cycle - returns summary"""
        now = datetime.now(timezone.utc)
        print(f"[{now.isoformat()}] Analyzing audit-gratuit visitors...")

        events_by_visitor = self.load_visitor_events()

        if not events_by_visitor:
            print("No visitor events found")
            return {"visitors": 0, "hot": 0, "sms": 0}

        sms_count = 0
        hot_count = 0

        for visitor_id, events in events_by_visitor.items():
            visitor_data = self.analyze_visitor(visitor_id, events)

            if self.is_hot_visitor(visitor_data):
                if not visitor_data.get("is_hot"):
                    visitor_data["is_hot"] = True
                    self.state["total_hot_detected"] += 1
                    hot_count += 1

                    print(f"HOT VISITOR: {visitor_id}")
                    print(f"  Time: {visitor_data['time_on_page']}s | Scroll: {visitor_data['scroll_depth']}%")
                    print(f"  IP: {visitor_data['ip']} | Device: {visitor_data['device']}")
                    print(f"  Referrer: {visitor_data['referrer']}")

                    if not visitor_data.get("alert_sent"):
                        sms_sent = self.send_sms_alert(visitor_id, visitor_data)

                        if sms_sent:
                            visitor_data["alert_sent"] = True
                            visitor_data["alert_sent_at"] = now.isoformat()
                            sms_count += 1

                        self.log_hot_alert(visitor_id, visitor_data, sms_sent)

        self.state["total_visitors"] = len(events_by_visitor)
        self.save_state()

        print(f"Analyzed {len(events_by_visitor)} visitors - {hot_count} HOT - {sms_count} SMS sent")
        return {"visitors": len(events_by_visitor), "hot": hot_count, "sms": sms_count}


def simulate_hot_visit() -> Dict:
    """Simulate a HOT visitor for testing purposes.
    Writes fake events to VISITOR_LOG and returns the simulation details.
    """
    visitor_id = f"test_{int(time.time())}_{os.getpid()}"
    now = datetime.now(timezone.utc)

    events = []
    # Page load
    events.append({
        "visitor_id": visitor_id,
        "type": "pageview",
        "timestamp": now.isoformat(),
        "page": "/audit-gratuit-monitoring.html",
        "ip": "203.0.113.42",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "referer": "https://www.google.com/search?q=monitoring+web+audit",
    })

    # Scrolls over 2.5 minutes
    for i in range(1, 6):
        t = now + timedelta(seconds=i * 30)
        events.append({
            "visitor_id": visitor_id,
            "type": "scroll",
            "timestamp": t.isoformat(),
            "page": "/audit-gratuit-monitoring.html",
            "depth": min(i * 20, 85),
            "ip": "203.0.113.42",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "referer": "https://www.google.com/search?q=monitoring+web+audit",
        })

    # Heartbeats showing 2.5 min on page
    for i in [60, 120, 150]:
        t = now + timedelta(seconds=i)
        events.append({
            "visitor_id": visitor_id,
            "type": "heartbeat",
            "timestamp": t.isoformat(),
            "page": "/audit-gratuit-monitoring.html",
            "time_on_page": i,
            "ip": "203.0.113.42",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "referer": "https://www.google.com/search?q=monitoring+web+audit",
        })

    # Form interaction (started but NOT submitted = abandoned)
    t = now + timedelta(seconds=100)
    events.append({
        "visitor_id": visitor_id,
        "type": "form_focus",
        "timestamp": t.isoformat(),
        "page": "/audit-gratuit-monitoring.html",
        "ip": "203.0.113.42",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "referer": "https://www.google.com/search?q=monitoring+web+audit",
    })

    # Write events to log
    Path(VISITOR_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(VISITOR_LOG, "a") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    print(f"Simulated HOT visitor: {visitor_id}")
    print(f"  IP: 203.0.113.42 (test)")
    print(f"  Referrer: google.com (monitoring web audit)")
    print(f"  Device: desktop (macOS)")
    print(f"  Time on page: 150s (>120s threshold)")
    print(f"  Scroll depth: 85% (>70% threshold)")
    print(f"  Form: started, NOT submitted (abandoned)")
    print(f"  Events written: {len(events)}")

    return {
        "visitor_id": visitor_id,
        "events_count": len(events),
        "time_on_page": 150,
        "scroll_depth": 85,
        "ip": "203.0.113.42",
        "referrer": "https://www.google.com/search?q=monitoring+web+audit",
        "device": "desktop",
    }


def main():
    """Main entry point - single cycle or simulation"""
    import argparse

    parser = argparse.ArgumentParser(description="HOT Visitor Tracker - /audit-gratuit")
    parser.add_argument("--simulate", action="store_true", help="Simulate a HOT visitor then analyze")
    parser.add_argument("--analyze-only", action="store_true", help="Run analysis only (no simulation)")
    args = parser.parse_args()

    print("=" * 70)
    print("HOT VISITOR TRACKER - /audit-gratuit-monitoring.html")
    print("=" * 70)
    print(f"HOT Criteria: time > {HOT_CRITERIA['time_on_page_min']}s OR scroll > {HOT_CRITERIA['scroll_depth_min']}%")
    print(f"SMS target: {SHAREHOLDER_PHONE}")
    print(f"HOT window: {HOT_WINDOW_MINUTES} min for manual follow-up")
    print("=" * 70)
    print()

    tracker = AuditGratuitHotTracker()

    # Initialize OVH SMS
    ovh_ok = tracker.init_ovh_client()
    if not ovh_ok:
        print("WARNING: OVH SMS not available - alerts logged only")
    print()

    if args.simulate:
        print("--- SIMULATION MODE ---")
        sim = simulate_hot_visit()
        print()

    # Run analysis cycle
    print("--- ANALYSIS ---")
    result = tracker.monitor_cycle()

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Total visitors: {result['visitors']}")
    print(f"HOT detected: {result['hot']}")
    print(f"SMS sent: {result['sms']}")
    print(f"State: {STATE_FILE}")
    print(f"Alerts log: {HOT_ALERTS_LOG}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
