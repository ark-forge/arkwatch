#!/usr/bin/env python3
"""
First 3 Customers - Slack Notifier
Lit le fichier de notifications et envoie des messages Slack pour chaque nouveau signup.
À exécuter en cron toutes les minutes.
"""

import json
import os
import time
from pathlib import Path

NOTIFICATION_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/first_3_notifications.log")
PROCESSED_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/first_3_processed.json")
SLACK_WEBHOOK = os.getenv("ARKFORGE_SLACK_WEBHOOK", "")  # À définir dans settings.env


def load_processed() -> set:
    """Charge la liste des signups déjà traités."""
    if not PROCESSED_FILE.exists():
        return set()
    try:
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
            return set(data.get("processed_emails", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_processed(processed: set):
    """Sauvegarde la liste des signups traités."""
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"processed_emails": list(processed)}, f, indent=2)


def send_slack_notification(signup_data: dict):
    """Envoie une notification Slack."""
    if not SLACK_WEBHOOK:
        print("⚠️  SLACK_WEBHOOK non défini, notification ignorée")
        return

    import requests

    spot_number = signup_data.get("spot_number", "?")
    email = signup_data.get("email", "?")
    company = signup_data.get("company", "?")
    usecase = signup_data.get("usecase", "?")
    linkedin = signup_data.get("linkedin", "N/A")
    source = signup_data.get("source", "direct")

    message = {
        "text": f"🔥 FIRST 3 CUSTOMER #{spot_number}!",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🔥 CUSTOMER #{spot_number} OF 3 SIGNED UP!"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Email:*\n{email}"},
                    {"type": "mrkdwn", "text": f"*Company:*\n{company}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{source}"},
                    {"type": "mrkdwn", "text": f"*Spots left:*\n{3 - spot_number}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Use Case:*\n{usecase}"},
            },
        ],
    }

    if linkedin and linkedin != "N/A":
        message["blocks"].append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*LinkedIn:* <{linkedin}|View Profile>"},
        })

    message["blocks"].append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"⏰ {signup_data.get('claimed_at', 'N/A')}"}],
    })

    try:
        response = requests.post(SLACK_WEBHOOK, json=message, timeout=5)
        if response.status_code == 200:
            print(f"✓ Notification Slack envoyée pour {email}")
        else:
            print(f"✗ Erreur Slack: {response.status_code}")
    except Exception as e:
        print(f"✗ Erreur réseau: {e}")


def main():
    """Traite les nouvelles notifications."""
    if not NOTIFICATION_FILE.exists():
        print("Aucune notification à traiter")
        return

    processed = load_processed()
    new_count = 0

    with open(NOTIFICATION_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                notification = json.loads(line)
                signup_data = notification.get("data", {})
                email = signup_data.get("email")

                if email and email not in processed:
                    send_slack_notification(signup_data)
                    processed.add(email)
                    new_count += 1
            except json.JSONDecodeError:
                print(f"✗ Ligne invalide: {line[:50]}...")
                continue

    if new_count > 0:
        save_processed(processed)
        print(f"✓ {new_count} nouvelle(s) notification(s) traitée(s)")
    else:
        print("Aucune nouvelle notification")


if __name__ == "__main__":
    main()
