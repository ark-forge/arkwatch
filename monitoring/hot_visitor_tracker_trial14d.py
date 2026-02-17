#!/usr/bin/env python3
"""
MONITORING TEMPS RÉEL - Visiteurs HOT page /trial-14d
Détecte les visiteurs à forte intention et envoie SMS shareholder pour intervention immédiate

GARDIEN TASK #20261197 - 2026-02-10
Objectif: Capter 100% des opportunités chaudes avant refroidissement
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
MONITOR_INTERVAL = 30  # 30 secondes - surveillance temps réel
SHAREHOLDER_PHONE = "+33749879812"  # Numéro shareholder
API_BASE_URL = "http://127.0.0.1:8080"

# Critères HOT visitor
HOT_CRITERIA = {
    "min_interactions": 3,  # 3+ interactions = HOT
    "form_abandoned": True,  # Formulaire commencé mais non envoyé
    "time_on_page_min": 45,  # 45+ secondes sur page = HOT
    "scroll_depth_min": 70,  # 70%+ scroll = engagement élevé
}

# Paths
VISITOR_LOG = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_visitors.jsonl"
HOT_ALERTS_LOG = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_hot_alerts.jsonl"
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/monitoring/hot_visitor_state.json"
OVH_CREDENTIALS = "/opt/claude-ceo/config/ovh_credentials.json"

# Cooldown: n'envoyer qu'1 SMS par visiteur par 24h
ALERT_COOLDOWN_HOURS = 24


class HotVisitorTracker:
    """Track visitors on /trial-14d and detect HOT leads"""

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

            # Test connectivity
            services = self.ovh_client.get('/sms')
            if not services:
                print("WARNING: No SMS services found in OVH account")
                return False

            print(f"✓ OVH SMS client initialized - {len(services)} service(s) available")
            return True

        except ImportError:
            print("ERROR: ovh library not installed - run: pip install ovh")
            return False
        except Exception as e:
            print(f"ERROR initializing OVH client: {e}")
            return False

    def send_sms_alert(self, visitor_id: str, visitor_data: Dict) -> bool:
        """Send SMS alert to shareholder via OVH"""
        if not self.ovh_client:
            print("WARNING: OVH client not initialized - cannot send SMS")
            return False

        # Check cooldown - 1 SMS max par visiteur par 24h
        if visitor_data.get("alert_sent_at"):
            last_alert = datetime.fromisoformat(visitor_data["alert_sent_at"])
            if (datetime.now(timezone.utc) - last_alert).total_seconds() < ALERT_COOLDOWN_HOURS * 3600:
                print(f"Cooldown active pour {visitor_id} - SMS non envoyé")
                return False

        try:
            # Get SMS service name
            services = self.ovh_client.get('/sms')
            if not services:
                print("ERROR: No SMS service available")
                return False

            service_name = services[0]

            # Build message
            interactions = visitor_data.get("interactions", 0)
            time_on_page = visitor_data.get("time_on_page", 0)
            form_started = visitor_data.get("form_started", False)

            message = (
                f"🔥 HOT VISITOR /trial-14d\n"
                f"ID: {visitor_id[:12]}\n"
                f"Interactions: {interactions}\n"
                f"Temps: {time_on_page}s\n"
                f"Form: {'Abandonné' if form_started and not visitor_data.get('form_submitted') else 'Non démarré'}\n"
                f"Action: RELANCE IMMÉDIATE!"
            )

            # Send SMS via OVH
            result = self.ovh_client.post(
                f'/sms/{service_name}/jobs',
                charset='UTF-8',
                message=message,
                receivers=[SHAREHOLDER_PHONE],
                sender='ArkWatch',  # Max 11 chars
                priority='high',
            )

            print(f"✓ SMS sent successfully via OVH - {result.get('totalCreditsRemoved', 0)} credits used")
            self.state["total_sms_sent"] += 1
            return True

        except Exception as e:
            print(f"ERROR sending SMS via OVH: {e}")
            return False

    def log_hot_alert(self, visitor_id: str, visitor_data: Dict, sms_sent: bool):
        """Log HOT visitor alert"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "visitor_id": visitor_id,
            "visitor_data": visitor_data,
            "sms_sent": sms_sent,
            "alert_type": "hot_visitor_trial_14d",
        }

        Path(HOT_ALERTS_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(HOT_ALERTS_LOG, "a") as f:
            f.write(json.dumps(alert) + "\n")

        self.hot_detected.append(alert)

    def analyze_visitor(self, visitor_id: str, events: List[Dict]) -> Dict:
        """Analyze visitor behavior and detect HOT signals"""
        visitor = self.visitors[visitor_id]

        for event in events:
            event_type = event.get("type")
            timestamp = event.get("timestamp")

            if not visitor["first_seen"]:
                visitor["first_seen"] = timestamp

            visitor["last_seen"] = timestamp

            # Count interactions
            if event_type in ["click", "scroll", "form_focus", "form_input"]:
                visitor["interactions"] += 1

            # Track scroll depth
            if event_type == "scroll":
                visitor["scroll_depth"] = max(visitor["scroll_depth"], event.get("depth", 0))

            # Track form interaction
            if event_type in ["form_focus", "form_input"]:
                visitor["form_started"] = True

            if event_type == "form_submit":
                visitor["form_submitted"] = True

        # Calculate time on page
        if visitor["first_seen"] and visitor["last_seen"]:
            first = datetime.fromisoformat(visitor["first_seen"])
            last = datetime.fromisoformat(visitor["last_seen"])
            visitor["time_on_page"] = int((last - first).total_seconds())

        return visitor

    def is_hot_visitor(self, visitor_data: Dict) -> bool:
        """Determine if visitor is HOT based on criteria"""
        # Critère 1: 3+ interactions
        if visitor_data["interactions"] >= HOT_CRITERIA["min_interactions"]:
            return True

        # Critère 2: Formulaire abandonné (démarré mais non soumis)
        if visitor_data["form_started"] and not visitor_data["form_submitted"]:
            return True

        # Critère 3: Temps sur page > 45s
        if visitor_data["time_on_page"] >= HOT_CRITERIA["time_on_page_min"]:
            return True

        # Critère 4: Scroll depth > 70%
        if visitor_data["scroll_depth"] >= HOT_CRITERIA["scroll_depth_min"]:
            return True

        return False

    def load_visitor_events(self) -> Dict[str, List[Dict]]:
        """Load visitor events from log file"""
        events_by_visitor = defaultdict(list)

        if not Path(VISITOR_LOG).exists():
            return events_by_visitor

        try:
            with open(VISITOR_LOG) as f:
                for line in f:
                    event = json.loads(line)
                    visitor_id = event.get("visitor_id") or event.get("ip", "unknown")
                    events_by_visitor[visitor_id].append(event)
        except Exception as e:
            print(f"ERROR loading visitor events: {e}")

        return events_by_visitor

    def monitor_visitors(self):
        """Monitor visitors and detect HOT leads"""
        print(f"[{datetime.now(timezone.utc).isoformat()}] Analyzing visitors...")

        # Load events
        events_by_visitor = self.load_visitor_events()

        if not events_by_visitor:
            print("No visitor events found")
            return

        # Analyze each visitor
        for visitor_id, events in events_by_visitor.items():
            visitor_data = self.analyze_visitor(visitor_id, events)

            # Check if HOT
            if self.is_hot_visitor(visitor_data):
                if not visitor_data.get("is_hot"):
                    # New HOT visitor detected
                    visitor_data["is_hot"] = True
                    self.state["total_hot_detected"] += 1

                    print(f"🔥 HOT VISITOR DETECTED: {visitor_id}")
                    print(f"   - Interactions: {visitor_data['interactions']}")
                    print(f"   - Time on page: {visitor_data['time_on_page']}s")
                    print(f"   - Form started: {visitor_data['form_started']}")
                    print(f"   - Form submitted: {visitor_data['form_submitted']}")

                    # Send SMS alert if not already sent
                    if not visitor_data.get("alert_sent"):
                        sms_sent = self.send_sms_alert(visitor_id, visitor_data)

                        if sms_sent:
                            visitor_data["alert_sent"] = True
                            visitor_data["alert_sent_at"] = datetime.now(timezone.utc).isoformat()

                        # Log alert
                        self.log_hot_alert(visitor_id, visitor_data, sms_sent)

        # Update state
        self.state["total_visitors"] = len(events_by_visitor)
        self.save_state()

        print(f"✓ Analyzed {len(events_by_visitor)} visitors - {len(self.hot_detected)} HOT detected this run")


def create_tracking_snippet() -> str:
    """Generate JavaScript tracking snippet to embed in /trial-14d.html"""
    snippet = """
<!-- HOT Visitor Tracking - ArkWatch Trial 14d -->
<script>
(function() {
    const TRACKING_ENDPOINT = '/api/track-visitor-trial14d';
    const VISITOR_ID = localStorage.getItem('visitor_id') ||
                      Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('visitor_id', VISITOR_ID);

    let interactions = 0;
    let scrollDepth = 0;
    let formStarted = false;
    const startTime = Date.now();

    function sendEvent(eventType, data = {}) {
        fetch(TRACKING_ENDPOINT, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                visitor_id: VISITOR_ID,
                type: eventType,
                timestamp: new Date().toISOString(),
                page: '/trial-14d',
                ...data
            })
        }).catch(e => console.error('Tracking error:', e));
    }

    // Track interactions
    document.addEventListener('click', () => {
        interactions++;
        sendEvent('click', {interactions});
    });

    // Track scroll depth
    window.addEventListener('scroll', () => {
        const depth = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
        if (depth > scrollDepth) {
            scrollDepth = depth;
            sendEvent('scroll', {depth: scrollDepth});
        }
    });

    // Track form interaction
    const formInputs = document.querySelectorAll('input[type="email"], textarea, select');
    formInputs.forEach(input => {
        input.addEventListener('focus', () => {
            if (!formStarted) {
                formStarted = true;
                sendEvent('form_focus');
            }
        });
        input.addEventListener('input', () => {
            sendEvent('form_input', {field: input.name || input.id});
        });
    });

    // Track form submission
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', () => {
            sendEvent('form_submit');
        });
    }

    // Track page visibility (tab switch)
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            const timeOnPage = Math.round((Date.now() - startTime) / 1000);
            sendEvent('page_leave', {time_on_page: timeOnPage, interactions, scrollDepth});
        }
    });

    // Send heartbeat every 30s
    setInterval(() => {
        const timeOnPage = Math.round((Date.now() - startTime) / 1000);
        sendEvent('heartbeat', {time_on_page: timeOnPage, interactions, scrollDepth});
    }, 30000);
})();
</script>
"""
    return snippet


def main():
    """Main monitoring loop"""
    print("=" * 80)
    print("HOT VISITOR TRACKER - /trial-14d Real-Time Monitoring")
    print("=" * 80)
    print(f"Task: #20261197 | Worker: GARDIEN")
    print(f"Interval: {MONITOR_INTERVAL}s")
    print(f"Shareholder: {SHAREHOLDER_PHONE}")
    print(f"HOT Criteria:")
    print(f"  - Min interactions: {HOT_CRITERIA['min_interactions']}")
    print(f"  - Form abandoned: {HOT_CRITERIA['form_abandoned']}")
    print(f"  - Time on page: {HOT_CRITERIA['time_on_page_min']}s")
    print(f"  - Scroll depth: {HOT_CRITERIA['scroll_depth_min']}%")
    print("=" * 80)
    print()

    tracker = HotVisitorTracker()

    # Initialize OVH SMS
    if not tracker.init_ovh_client():
        print("⚠️  WARNING: OVH SMS not available - alerts will be logged only")
        print()

    # Generate tracking snippet
    snippet = create_tracking_snippet()
    snippet_path = "/opt/claude-ceo/workspace/arkwatch/site/tracking_snippet_trial14d.html"
    Path(snippet_path).parent.mkdir(parents=True, exist_ok=True)
    with open(snippet_path, "w") as f:
        f.write(snippet)
    print(f"✓ Tracking snippet generated: {snippet_path}")
    print("  → Embed this snippet in /trial-14d.html before </body>")
    print()

    # Run monitoring
    try:
        tracker.monitor_visitors()
        print()
        print("=" * 80)
        print("MONITORING CYCLE COMPLETE")
        print("=" * 80)
        print(f"Total visitors: {tracker.state['total_visitors']}")
        print(f"HOT detected: {tracker.state['total_hot_detected']}")
        print(f"SMS sent: {tracker.state['total_sms_sent']}")
        print(f"State saved: {STATE_FILE}")
        print(f"Alerts log: {HOT_ALERTS_LOG}")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")
        tracker.save_state()

    return 0


if __name__ == "__main__":
    sys.exit(main())
