"""Trial Tracker - Monitor trial activations and conversions for ArkWatch

This script tracks:
- Trial activations (when user starts using ArkWatch after signup)
- First API call timestamp
- Conversion events (trial -> paying customer)
- Engagement metrics

Used to alert fondations when a trial user becomes active (conversion opportunity)
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
TRIAL_SIGNUPS_FILE = DATA_DIR / "trial_14d_signups.json"
TRIAL_ACTIVITY_FILE = DATA_DIR / "trial_activity.json"
DB_FILE = Path("/opt/claude-ceo/workspace/arkwatch/data/arkwatch.db")


def get_db_connection():
    """Get SQLite database connection."""
    return sqlite3.connect(str(DB_FILE))


def load_trial_signups() -> list[dict]:
    """Load all trial signups from file."""
    if not TRIAL_SIGNUPS_FILE.exists():
        return []
    try:
        with open(TRIAL_SIGNUPS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def load_trial_activity() -> dict:
    """Load trial activity tracking data."""
    if not TRIAL_ACTIVITY_FILE.exists():
        return {"trials": {}, "last_check": None}
    try:
        with open(TRIAL_ACTIVITY_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"trials": {}, "last_check": None}


def save_trial_activity(data: dict):
    """Save trial activity tracking data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(TRIAL_ACTIVITY_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(TRIAL_ACTIVITY_FILE))


def get_user_activity(email: str) -> dict:
    """Get activity data for a specific user from database.

    Returns:
        {
            "has_api_key": bool,
            "watches_count": int,
            "checks_count": int,
            "last_check_at": str | None,
            "created_at": str | None
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    result = {
        "has_api_key": False,
        "watches_count": 0,
        "checks_count": 0,
        "last_check_at": None,
        "created_at": None
    }

    try:
        # Check if user exists and has API key
        cursor.execute("""
            SELECT created_at FROM users WHERE email = ?
        """, (email,))
        user_row = cursor.fetchone()

        if user_row:
            result["has_api_key"] = True
            result["created_at"] = user_row[0]

            # Count watches
            cursor.execute("""
                SELECT COUNT(*) FROM watches WHERE user_email = ?
            """, (email,))
            result["watches_count"] = cursor.fetchone()[0]

            # Count checks and get last check time
            cursor.execute("""
                SELECT COUNT(*), MAX(checked_at)
                FROM watch_checks
                WHERE watch_id IN (SELECT id FROM watches WHERE user_email = ?)
            """, (email,))
            check_row = cursor.fetchone()
            if check_row:
                result["checks_count"] = check_row[0] or 0
                result["last_check_at"] = check_row[1]

    finally:
        conn.close()

    return result


def check_trial_activation(email: str, activity_data: dict) -> dict | None:
    """Check if a trial user has activated (made first API call).

    Returns alert data if newly activated, None otherwise.
    """
    trials = activity_data.get("trials", {})

    # Skip if already marked as activated
    if email in trials and trials[email].get("activated"):
        return None

    # Get current activity
    user_activity = get_user_activity(email)

    # Check for activation signals
    is_activated = (
        user_activity["watches_count"] > 0 or
        user_activity["checks_count"] > 0
    )

    if not is_activated:
        return None

    # User just activated!
    activation_time = user_activity["last_check_at"] or user_activity["created_at"]

    # Update tracking
    trials[email] = {
        "activated": True,
        "activated_at": activation_time or datetime.utcnow().isoformat(),
        "watches_count": user_activity["watches_count"],
        "checks_count": user_activity["checks_count"],
        "notified_fondations": False
    }

    return {
        "email": email,
        "activated_at": trials[email]["activated_at"],
        "watches_count": user_activity["watches_count"],
        "checks_count": user_activity["checks_count"]
    }


def check_conversion(email: str, activity_data: dict) -> dict | None:
    """Check if a trial user has converted to paying customer.

    Returns conversion data if converted, None otherwise.
    """
    trials = activity_data.get("trials", {})

    # Skip if already marked as converted
    if email in trials and trials[email].get("converted"):
        return None

    # Check if user has paying subscription
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT tier, subscription_status, stripe_customer_id
            FROM users
            WHERE email = ? AND tier != 'free' AND subscription_status = 'active'
        """, (email,))

        row = cursor.fetchone()

        if row:
            tier, status, customer_id = row

            # User converted!
            if email not in trials:
                trials[email] = {}

            trials[email]["converted"] = True
            trials[email]["converted_at"] = datetime.utcnow().isoformat()
            trials[email]["converted_to_tier"] = tier
            trials[email]["stripe_customer_id"] = customer_id

            return {
                "email": email,
                "converted_at": trials[email]["converted_at"],
                "tier": tier,
                "customer_id": customer_id
            }

    finally:
        conn.close()

    return None


def send_activation_alert(activation_data: dict):
    """Send alert to fondations when trial activates (conversion opportunity)."""
    import subprocess

    subject = f"🎯 TRIAL ACTIVATED - Conversion Opportunity: {activation_data['email']}"
    body = f"""NOUVEAU TRIAL ACTIVÉ - OPPORTUNITÉ DE CONVERSION

Email: {activation_data['email']}
Activé le: {activation_data['activated_at']}

Activité détectée:
- Watches créés: {activation_data['watches_count']}
- Checks exécutés: {activation_data['checks_count']}

🎯 ACTION RECOMMANDÉE:
1. Envoyer email de bienvenue personnalisé sous 24h
2. Proposer démo/onboarding si >3 watches
3. Surveiller engagement J+3, J+7
4. Préparer offre de conversion avant J+14

Dashboard: https://watch.arkforge.fr/api/trial-14d/stats
"""

    try:
        subprocess.run([
            "python3",
            "/opt/claude-ceo/automation/email_sender.py",
            "apps.desiorac@gmail.com",  # CEO/Fondations
            subject,
            body
        ], timeout=10, check=False, capture_output=True)
    except Exception:
        pass  # Best effort


def send_conversion_alert(conversion_data: dict):
    """Send alert when trial converts to paying customer."""
    import subprocess

    subject = f"💰 CONVERSION RÉUSSIE - Premier client: {conversion_data['email']}"
    body = f"""🎉 TRIAL CONVERTI EN CLIENT PAYANT

Email: {conversion_data['email']}
Converti le: {conversion_data['converted_at']}
Plan: {conversion_data['tier']}
Customer ID: {conversion_data['customer_id']}

🎯 PREMIER REVENU ARKWATCH EN APPROCHE
Le paiement sera enregistré après validation du webhook Stripe.

Actions automatiques:
✅ Tier mis à jour dans la BDD
✅ Limites augmentées automatiquement
✅ Email de confirmation envoyé

Prochaines étapes CEO:
1. Vérifier revenus dans payments.json sous 24h
2. Contacter client pour feedback
3. Demander témoignage/case study
4. Optimiser funnel basé sur ce succès

Dashboard: https://watch.arkforge.fr/api/trial-14d/stats
"""

    try:
        subprocess.run([
            "python3",
            "/opt/claude-ceo/automation/email_sender.py",
            "apps.desiorac@gmail.com",
            subject,
            body
        ], timeout=10, check=False, capture_output=True)
    except Exception:
        pass


def run_tracking_cycle():
    """Main tracking cycle - check all trials for activation and conversion."""
    signups = load_trial_signups()
    activity_data = load_trial_activity()

    now = datetime.utcnow()
    activity_data["last_check"] = now.isoformat()

    activations = []
    conversions = []

    for signup in signups:
        email = signup["email"]

        # Check for activation
        activation = check_trial_activation(email, activity_data)
        if activation:
            activations.append(activation)
            send_activation_alert(activation)
            activity_data["trials"][email]["notified_fondations"] = True

        # Check for conversion
        conversion = check_conversion(email, activity_data)
        if conversion:
            conversions.append(conversion)
            send_conversion_alert(conversion)

    # Save updated tracking data
    save_trial_activity(activity_data)

    return {
        "checked_at": now.isoformat(),
        "total_signups": len(signups),
        "new_activations": len(activations),
        "new_conversions": len(conversions),
        "activations": activations,
        "conversions": conversions
    }


def get_trial_stats() -> dict:
    """Get current trial statistics."""
    signups = load_trial_signups()
    activity_data = load_trial_activity()
    trials = activity_data.get("trials", {})

    activated_count = sum(1 for t in trials.values() if t.get("activated"))
    converted_count = sum(1 for t in trials.values() if t.get("converted"))

    # Calculate conversion rate
    conversion_rate = (converted_count / activated_count * 100) if activated_count > 0 else 0

    return {
        "total_signups": len(signups),
        "activated_trials": activated_count,
        "paying_customers": converted_count,
        "conversion_rate": round(conversion_rate, 1),
        "last_check": activity_data.get("last_check")
    }


if __name__ == "__main__":
    # Run tracking cycle
    result = run_tracking_cycle()
    print(json.dumps(result, indent=2))
