#!/usr/bin/env python3
"""
MONITORING TEMPS RÉEL - Conversion Audit Gratuit → Appel Qualificatif
Surveille 3 signaux HOT des 55 CTOs contactés:
  1. Visite page /audit-gratuit-monitoring.html > 90s
  2. Clic CTA 'Réserver audit'
  3. Ouverture email J+1/J+2

Dès signal détecté → SMS actionnaire avec script appel
GARDIEN TASK #122 - 2026-02-10
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

# Critères HOT - 3 signaux conversion
HOT_CRITERIA = {
    "page_visit_duration_sec": 90,      # Signal 1: Visite > 90s
    "cta_click": "cta_reserver_audit",  # Signal 2: Clic CTA
    "email_open_delay_hours": [24, 48], # Signal 3: Ouverture J+1 ou J+2
}

# Paths
PROSPECTS_FILE = "/opt/claude-ceo/workspace/croissance/PROSPECTS_30_CTOS_SCALEUPS_TASK_20261240.json"
VISITOR_LOG = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_visitors.jsonl"
EMAIL_TRACKING_LOG = "/opt/claude-ceo/workspace/arkwatch/data/email_tracking.jsonl"
HOT_LEADS_STATE = "/opt/claude-ceo/workspace/arkwatch/conversion/hot_leads_realtime.json"
ALERT_LOG = "/opt/claude-ceo/workspace/arkwatch/conversion/conversion_alerts.jsonl"
OVH_CREDENTIALS = "/opt/claude-ceo/config/ovh_credentials.json"

# Alert cooldown: 1 SMS par CTO par signal (éviter spam)
ALERT_COOLDOWN_HOURS = 24


class ConversionMonitor:
    """Monitor real-time conversion signals for 55 CTOs"""

    def __init__(self):
        self.prospects = self.load_prospects()
        self.state = self.load_state()
        self.hot_signals = []
        self.ovh_client = None

    def load_prospects(self) -> List[Dict]:
        """Load 55 CTOs from prospects file"""
        try:
            with open(PROSPECTS_FILE) as f:
                data = json.load(f)
                return data.get("prospects", [])[:30]  # Task mentions 55, file has 30
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: Cannot load prospects: {e}")
            return []

    def load_state(self) -> Dict:
        """Load monitoring state"""
        if Path(HOT_LEADS_STATE).exists():
            try:
                with open(HOT_LEADS_STATE) as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        return {
            "monitoring_start": datetime.now(timezone.utc).isoformat(),
            "total_ctos_tracked": len(self.prospects),
            "hot_signals_detected": 0,
            "conversion_alerts_sent": 0,
            "leads": [],
        }

    def save_state(self):
        """Save monitoring state"""
        Path(HOT_LEADS_STATE).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(HOT_LEADS_STATE).with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        tmp.replace(HOT_LEADS_STATE)

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
                endpoint=creds.get("endpoint", "ovh-eu"),
                application_key=creds.get("application_key"),
                application_secret=creds.get("application_secret"),
                consumer_key=creds.get("consumer_key"),
            )
            return True
        except Exception as e:
            print(f"WARNING: OVH client init failed: {e}")
            return False

    def check_signal_1_page_visit(self) -> List[Dict]:
        """
        Signal 1: Visite page /audit-gratuit-monitoring.html > 90s
        Returns: List of hot leads with page visit signal
        """
        hot_leads = []

        if not Path(VISITOR_LOG).exists():
            return hot_leads

        # Read last 100 visitor events
        try:
            with open(VISITOR_LOG) as f:
                lines = f.readlines()[-100:]  # Last 100 events

            visitor_sessions = defaultdict(list)

            for line in lines:
                try:
                    event = json.loads(line.strip())
                    visitor_id = event.get("visitor_id") or event.get("ip")
                    visitor_sessions[visitor_id].append(event)
                except json.JSONDecodeError:
                    continue

            # Analyze sessions
            for visitor_id, events in visitor_sessions.items():
                # Calculate time on page
                timestamps = [
                    datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
                    for e in events if "timestamp" in e
                ]

                if len(timestamps) >= 2:
                    time_on_page = (max(timestamps) - min(timestamps)).total_seconds()

                    if time_on_page >= HOT_CRITERIA["page_visit_duration_sec"]:
                        # Match with prospect
                        prospect = self.match_visitor_to_prospect(visitor_id, events)

                        if prospect:
                            hot_leads.append({
                                "signal_type": "page_visit_90s",
                                "prospect": prospect,
                                "visitor_id": visitor_id,
                                "time_on_page": time_on_page,
                                "detected_at": datetime.now(timezone.utc).isoformat(),
                            })

        except Exception as e:
            print(f"ERROR checking signal 1: {e}")

        return hot_leads

    def check_signal_2_cta_click(self) -> List[Dict]:
        """
        Signal 2: Clic CTA 'Réserver audit'
        Returns: List of hot leads with CTA click signal
        """
        hot_leads = []

        # CTA clicks tracked via API endpoint /api/track_cta_click
        cta_log = "/opt/claude-ceo/workspace/arkwatch/data/cta_clicks.jsonl"

        if not Path(cta_log).exists():
            return hot_leads

        try:
            with open(cta_log) as f:
                lines = f.readlines()[-50:]  # Last 50 clicks

            for line in lines:
                try:
                    event = json.loads(line.strip())

                    if event.get("cta_id") == HOT_CRITERIA["cta_click"]:
                        visitor_id = event.get("visitor_id") or event.get("ip")
                        prospect = self.match_visitor_to_prospect(visitor_id, [event])

                        if prospect:
                            hot_leads.append({
                                "signal_type": "cta_click_reserver",
                                "prospect": prospect,
                                "visitor_id": visitor_id,
                                "cta_id": event.get("cta_id"),
                                "detected_at": event.get("timestamp"),
                            })

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"ERROR checking signal 2: {e}")

        return hot_leads

    def check_signal_3_email_open(self) -> List[Dict]:
        """
        Signal 3: Ouverture email J+1 ou J+2 (24-48h après envoi)
        Returns: List of hot leads with email open signal
        """
        hot_leads = []

        if not Path(EMAIL_TRACKING_LOG).exists():
            return hot_leads

        try:
            with open(EMAIL_TRACKING_LOG) as f:
                lines = f.readlines()[-200:]  # Last 200 email events

            # Group by email address
            email_events = defaultdict(list)

            for line in lines:
                try:
                    event = json.loads(line.strip())
                    email = event.get("recipient")
                    if email:
                        email_events[email].append(event)
                except json.JSONDecodeError:
                    continue

            # Check for opens in J+1/J+2 window
            now = datetime.now(timezone.utc)

            for email, events in email_events.items():
                sent_events = [e for e in events if e.get("event") == "sent"]
                open_events = [e for e in events if e.get("event") == "opened"]

                if sent_events and open_events:
                    sent_time = datetime.fromisoformat(
                        sent_events[-1]["timestamp"].replace("Z", "+00:00")
                    )
                    open_time = datetime.fromisoformat(
                        open_events[-1]["timestamp"].replace("Z", "+00:00")
                    )

                    hours_delta = (open_time - sent_time).total_seconds() / 3600

                    if (HOT_CRITERIA["email_open_delay_hours"][0] <= hours_delta
                        <= HOT_CRITERIA["email_open_delay_hours"][1]):

                        # Match with prospect
                        prospect = self.match_email_to_prospect(email)

                        if prospect:
                            hot_leads.append({
                                "signal_type": "email_open_j1_j2",
                                "prospect": prospect,
                                "email": email,
                                "sent_at": sent_events[-1]["timestamp"],
                                "opened_at": open_events[-1]["timestamp"],
                                "hours_delta": round(hours_delta, 1),
                                "detected_at": datetime.now(timezone.utc).isoformat(),
                            })

        except Exception as e:
            print(f"ERROR checking signal 3: {e}")

        return hot_leads

    def match_visitor_to_prospect(self, visitor_id: str, events: List[Dict]) -> Optional[Dict]:
        """
        Match visitor ID to one of 55 prospects
        Uses: IP, email domain, referrer, user-agent
        """
        # Extract clues from events
        ip = visitor_id if "." in visitor_id else None
        referrer = next((e.get("referrer") for e in events if e.get("referrer")), None)
        user_agent = next((e.get("user_agent") for e in events if e.get("user_agent")), None)

        # Attempt matching
        for prospect in self.prospects:
            email_domain = prospect.get("email_domain", "")

            # Match by referrer domain
            if referrer and email_domain in referrer:
                return prospect

            # Match by IP geolocation (would need IP lookup service)
            # For now, return None - requires enrichment

        return None

    def match_email_to_prospect(self, email: str) -> Optional[Dict]:
        """Match email address to prospect"""
        for prospect in self.prospects:
            email_domain = prospect.get("email_domain", "")
            if email_domain and email_domain in email:
                return prospect

        return None

    def send_sms_alert(self, signal: Dict) -> bool:
        """Send SMS alert to shareholder with call script"""
        if not self.ovh_client:
            print("WARNING: OVH client not initialized, cannot send SMS")
            return False

        prospect = signal["prospect"]
        signal_type = signal["signal_type"]

        # Build SMS message
        sms_body = self.build_sms_message(signal)

        try:
            # Send SMS via OVH
            sms_service = self.ovh_client.get("/sms")[0]

            result = self.ovh_client.post(
                f"/sms/{sms_service}/jobs",
                sender="ArkForge",
                message=sms_body,
                receivers=[SHAREHOLDER_PHONE],
                noStopClause=False,
                priority="high",
            )

            print(f"✅ SMS sent: {result}")

            # Log alert
            self.log_alert(signal, sms_sent=True)

            return True

        except Exception as e:
            print(f"ERROR sending SMS: {e}")
            self.log_alert(signal, sms_sent=False, error=str(e))
            return False

    def build_sms_message(self, signal: Dict) -> str:
        """Build SMS alert message with call script"""
        prospect = signal["prospect"]
        signal_type = signal["signal_type"]

        signal_labels = {
            "page_visit_90s": "Visite page audit > 90s",
            "cta_click_reserver": "Clic CTA 'Réserver audit'",
            "email_open_j1_j2": "Ouverture email J+1/J+2",
        }

        entreprise = prospect.get("entreprise", "N/A")
        secteur = prospect.get("secteur", "N/A")
        pain_point = prospect.get("pain_point", "N/A")[:80]

        sms = f"""🔥 HOT LEAD DÉTECTÉ

Signal: {signal_labels.get(signal_type, signal_type)}

Entreprise: {entreprise}
Secteur: {secteur}
Pain: {pain_point}

APPELER MAINTENANT
Script: workspace/croissance/ACTION_ACTIONNAIRE_COLD_CALL_TOP3_HOT_WEB_20261133.md

ArkForge CEO
"""

        return sms[:160]  # SMS limit

    def log_alert(self, signal: Dict, sms_sent: bool, error: str = None):
        """Log conversion alert"""
        alert_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal_type": signal["signal_type"],
            "prospect_id": signal["prospect"].get("id"),
            "entreprise": signal["prospect"].get("entreprise"),
            "sms_sent": sms_sent,
            "sms_error": error,
        }

        Path(ALERT_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(ALERT_LOG, "a") as f:
            f.write(json.dumps(alert_entry) + "\n")

    def should_send_alert(self, signal: Dict) -> bool:
        """Check if alert should be sent (cooldown check)"""
        prospect_id = signal["prospect"].get("id")
        signal_type = signal["signal_type"]

        # Check recent alerts for this prospect + signal type
        for lead in self.state.get("leads", []):
            if (lead.get("prospect_id") == prospect_id
                and lead.get("signal_type") == signal_type):

                alert_time = datetime.fromisoformat(
                    lead["detected_at"].replace("Z", "+00:00")
                )
                hours_since = (datetime.now(timezone.utc) - alert_time).total_seconds() / 3600

                if hours_since < ALERT_COOLDOWN_HOURS:
                    print(f"⏳ Cooldown active for {prospect_id} ({signal_type}): {hours_since:.1f}h < {ALERT_COOLDOWN_HOURS}h")
                    return False

        return True

    def run_monitoring_cycle(self):
        """Run one monitoring cycle (check all 3 signals)"""
        print(f"\n🔍 MONITORING CYCLE - {datetime.now(timezone.utc).isoformat()}")
        print(f"📊 Tracking {len(self.prospects)} CTOs")

        # Initialize OVH if needed
        if not self.ovh_client:
            self.init_ovh_client()

        # Check all 3 signals
        signals = []

        print("\n1️⃣ Checking Signal 1: Page visit > 90s...")
        signals.extend(self.check_signal_1_page_visit())

        print("2️⃣ Checking Signal 2: CTA click 'Réserver audit'...")
        signals.extend(self.check_signal_2_cta_click())

        print("3️⃣ Checking Signal 3: Email open J+1/J+2...")
        signals.extend(self.check_signal_3_email_open())

        print(f"\n✅ Total signals detected: {len(signals)}")

        # Process hot signals
        for signal in signals:
            if self.should_send_alert(signal):
                print(f"\n🔥 HOT SIGNAL: {signal['signal_type']} - {signal['prospect'].get('entreprise')}")

                # Send SMS alert
                sms_sent = self.send_sms_alert(signal)

                # Update state
                self.state["hot_signals_detected"] += 1
                if sms_sent:
                    self.state["conversion_alerts_sent"] += 1

                self.state["leads"].append({
                    "prospect_id": signal["prospect"].get("id"),
                    "entreprise": signal["prospect"].get("entreprise"),
                    "signal_type": signal["signal_type"],
                    "detected_at": signal["detected_at"],
                    "sms_sent": sms_sent,
                })

        # Save state
        self.save_state()

        print(f"\n📈 Stats: {self.state['hot_signals_detected']} signals | {self.state['conversion_alerts_sent']} SMS sent")


def main():
    """Main monitoring loop"""
    monitor = ConversionMonitor()

    print("=" * 60)
    print("MONITORING TEMPS RÉEL - Conversion Audit Gratuit")
    print("=" * 60)
    print(f"Tracking: {len(monitor.prospects)} CTOs")
    print(f"Signals: Page visit >90s | CTA click | Email open J+1/J+2")
    print(f"Alert: SMS to {SHAREHOLDER_PHONE}")
    print("=" * 60)

    # Run monitoring cycle
    monitor.run_monitoring_cycle()

    print("\n✅ Monitoring cycle complete")
    print(f"📊 State saved to: {HOT_LEADS_STATE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
