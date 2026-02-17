#!/usr/bin/env python3
"""Trial Leads Monitor - Alert when email leads become trial users

Monitors email conversations and trial signups to detect when a lead
becomes an active trial user, triggering conversion opportunity alerts.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
EMAIL_CONVERSATIONS_FILE = Path("/opt/claude-ceo/shareholder/email_conversations.json")
TRIAL_SIGNUPS_FILE = DATA_DIR / "trial_14d_signups.json"
TRIAL_ACTIVITY_FILE = DATA_DIR / "trial_activity.json"
LEADS_STATE_FILE = DATA_DIR / "trial_leads_state.json"


def load_json(file_path: Path):
    """Load JSON file."""
    if not file_path.exists():
        return [] if "conversations" in str(file_path) else {}
    try:
        with open(file_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return [] if "conversations" in str(file_path) else {}


def save_json(file_path: Path, data):
    """Save JSON file atomically."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(file_path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    import os
    os.replace(tmp, str(file_path))


def send_alert(subject: str, body: str):
    """Send email alert."""
    try:
        subprocess.run([
            "python3",
            "/opt/claude-ceo/automation/email_sender.py",
            "apps.desiorac@gmail.com",
            subject,
            body
        ], timeout=15, check=False, capture_output=True)
    except Exception:
        pass


def extract_email_leads():
    """Extract email addresses from recent email conversations."""
    conversations = load_json(EMAIL_CONVERSATIONS_FILE)
    
    # Get emails from last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    recent_leads = set()
    
    for conv in conversations:
        try:
            conv_date = datetime.fromisoformat(conv.get("timestamp", "").replace("Z", "+00:00"))
            if conv_date >= cutoff:
                sender = conv.get("from", "")
                if "@" in sender and "arkforge" not in sender.lower():
                    # Extract email from "Name <email@domain.com>" format
                    if "<" in sender and ">" in sender:
                        email = sender.split("<")[1].split(">")[0].strip().lower()
                    else:
                        email = sender.strip().lower()
                    recent_leads.add(email)
        except Exception:
            continue
    
    return list(recent_leads)


def check_lead_conversions():
    """Check if any email leads have signed up for trial."""
    email_leads = extract_email_leads()
    signups = load_json(TRIAL_SIGNUPS_FILE)
    activity = load_json(TRIAL_ACTIVITY_FILE)
    leads_state = load_json(LEADS_STATE_FILE)
    
    notified_leads = leads_state.get("notified_leads", {})
    signup_emails = {s["email"] for s in signups}
    trials_data = activity.get("trials", {})
    
    new_conversions = []
    
    for lead_email in email_leads:
        if lead_email in signup_emails:
            # Lead has signed up!
            if lead_email not in notified_leads:
                # Get signup and activity info
                signup_info = next((s for s in signups if s["email"] == lead_email), None)
                activity_info = trials_data.get(lead_email, {})
                
                is_activated = activity_info.get("activated", False)
                
                conversion_data = {
                    "email": lead_email,
                    "signed_up_at": signup_info.get("registered_at") if signup_info else None,
                    "activated": is_activated,
                    "source": signup_info.get("source") if signup_info else "unknown"
                }
                
                new_conversions.append(conversion_data)
                notified_leads[lead_email] = {
                    "notified_at": datetime.utcnow().isoformat(),
                    "activated": is_activated
                }
    
    # Save updated state
    if new_conversions:
        leads_state["notified_leads"] = notified_leads
        save_json(LEADS_STATE_FILE, leads_state)
    
    return new_conversions


def send_lead_conversion_alert(conversion: dict):
    """Alert when email lead becomes trial user."""
    status = "ACTIVÉ ET UTILISE LE PRODUIT" if conversion["activated"] else "INSCRIT (pas encore activé)"
    
    subject = f"🎯 EMAIL LEAD → TRIAL USER: {conversion['email']}"
    body = f"""✅ LEAD EMAIL CONVERTI EN TRIAL

Email: {conversion['email']}
Inscription: {conversion['signed_up_at']}
Source: {conversion['source']}
Status: {status}

{'✅' if conversion['activated'] else '⚠️'} ACTIVATION: {"Oui - utilisateur actif!" if conversion['activated'] else "Non - en attente"}

🎯 OPPORTUNITÉ DE CONVERSION MAXIMALE:
Cette personne a:
1. Échangé par email avec nous
2. Décidé de s'inscrire au trial 14j
3. {"Commencé à utiliser le produit" if conversion['activated'] else "Pas encore commencé (action requise!)"}

{'ACTION IMMÉDIATE (utilisateur actif):' if conversion['activated'] else 'ACTION URGENTE (utilisateur passif):'}
1. {"Email de suivi personnalisé sous 24h" if conversion['activated'] else "Email d'onboarding + aide sous 4h"}
2. {"Proposer démo avancée / use cases" if conversion['activated'] else "Comprendre blocage, proposer démo live"}
3. {"Préparer offre commerciale avant J+14" if conversion['activated'] else "Activer l'utilisateur AVANT fin de trial"}
4. {"Demander feedback produit" if conversion['activated'] else "Offrir support technique prioritaire"}

Dashboard trial: https://watch.arkforge.fr/api/trial-14d/stats
Tracker activité: cd /opt/claude-ceo/workspace/arkwatch/conversion && python3 trial_tracker.py
"""
    
    send_alert(subject, body)


def check_nurturing_status():
    """Check and report nurturing sequence status for active leads."""
    nurturing_state_file = DATA_DIR / "nurturing_state.json"
    state = load_json(nurturing_state_file)
    if not state or not state.get("leads"):
        return

    leads = state.get("leads", {})
    metrics = state.get("metrics", {})
    active_count = sum(1 for l in leads.values() if not l.get("unsubscribed"))
    total_sent = metrics.get("total_sent", 0)

    print(f"\n📬 Nurturing sequence status:")
    print(f"   Active leads: {active_count}")
    print(f"   Emails sent: {total_sent}")

    opens = metrics.get("opens", {})
    clicks = metrics.get("clicks", {})
    if opens:
        print(f"   Opens by step: {opens}")
    if clicks:
        print(f"   Clicks by step: {clicks}")


def main():
    """Main monitoring routine."""
    print("📧 ArkWatch Trial Leads Monitor")
    print("=" * 60)

    print("\n🔍 Checking for email lead → trial conversions...")
    conversions = check_lead_conversions()

    if conversions:
        print(f"   ✅ Found {len(conversions)} new lead→trial conversions!")
        for conv in conversions:
            status = "ACTIVATED ✓" if conv["activated"] else "Not activated yet"
            print(f"      - {conv['email']} ({status})")
            send_lead_conversion_alert(conv)
        print(f"\n   📧 Sent {len(conversions)} conversion alerts")
    else:
        print("   ℹ️  No new lead conversions detected")

    # Report nurturing sequence status
    check_nurturing_status()

    print("\n" + "=" * 60)
    print("✓ Monitoring cycle complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
