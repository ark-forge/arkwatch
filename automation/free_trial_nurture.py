#!/usr/bin/env python3
"""
Free Trial Nurture System - ArkWatch

Surveille les utilisateurs en période d'essai gratuit et envoie des emails
de nurturing pour les accompagner vers la conversion.

Phases:
1. Signup (J+0): Bienvenue + guide de démarrage
2. Activation (J+1-3): Rappel si pas encore créé de surveillance
3. Engagement (J+7-14): Tips & best practices
4. Conversion (J+21): Fin de période gratuite, passage payant
5. Retention (J+30+): Suivi post-conversion

Conformité:
- Respecte RGPD (consentement implicite lors de l'inscription)
- Lien de désinscription dans chaque email
- Pas de spam (fréquence limitée)
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Paths
BASE_DIR = Path("/opt/claude-ceo/workspace/arkwatch")
DATA_DIR = BASE_DIR / "data"
SIGNUPS_FILE = DATA_DIR / "free_trial_signups.json"
API_KEYS_FILE = DATA_DIR / "api_keys.json"
NURTURE_LOG_FILE = DATA_DIR / "nurture_log.json"
EMAIL_SENDER = "/opt/claude-ceo/automation/email_sender.py"

# Configuration
TRIAL_DURATION_DAYS = 180  # 6 months
EMAIL_FROM = "contact@arkforge.fr"
EMAIL_FROM_NAME = "ArkWatch Team"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "nurture.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_json(filepath: Path) -> list[dict[str, Any]]:
    """Load JSON file safely."""
    if not filepath.exists():
        return []
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load {filepath}: {e}")
        return []


def save_json(filepath: Path, data: list[dict[str, Any]]):
    """Save JSON file safely with atomic write."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp = filepath.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(filepath)
    except OSError as e:
        logger.error(f"Failed to save {filepath}: {e}")
        if tmp.exists():
            tmp.unlink()


def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via email_sender.py."""
    try:
        result = subprocess.run(
            ["python3", str(EMAIL_SENDER), to, subject, body],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            logger.info(f"Email sent to {to}: {subject}")
            return True
        else:
            logger.error(f"Email failed for {to}: {result.stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"Email exception for {to}: {e}")
        return False


def has_activated_account(email: str) -> bool:
    """Check if user has created an API key (activated their account)."""
    api_keys = load_json(API_KEYS_FILE)
    return any(
        key.get("user_email", "").lower() == email.lower() for key in api_keys
    )


def has_created_watches(email: str) -> bool:
    """Check if user has created at least one watch."""
    watches_file = DATA_DIR / "watches.json"
    watches = load_json(watches_file)
    return any(
        watch.get("user_email", "").lower() == email.lower() for watch in watches
    )


def get_nurture_log(email: str) -> dict[str, Any]:
    """Get nurture log for a specific email."""
    logs = load_json(NURTURE_LOG_FILE)
    for log in logs:
        if log.get("email", "").lower() == email.lower():
            return log
    return {}


def update_nurture_log(email: str, event: str, metadata: dict[str, Any] | None = None):
    """Update nurture log with new event."""
    logs = load_json(NURTURE_LOG_FILE)

    # Find existing log or create new
    log_entry = None
    for log in logs:
        if log.get("email", "").lower() == email.lower():
            log_entry = log
            break

    if log_entry is None:
        log_entry = {
            "email": email,
            "events": [],
            "created_at": datetime.utcnow().isoformat(),
        }
        logs.append(log_entry)

    # Add event
    log_entry["events"].append({
        "type": event,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    })
    log_entry["updated_at"] = datetime.utcnow().isoformat()

    save_json(NURTURE_LOG_FILE, logs)


def send_welcome_email(email: str, signup_data: dict[str, Any]) -> bool:
    """Send welcome email (Phase 1: Signup, J+0)."""
    subject = "Bienvenue sur ArkWatch - Commencez votre essai gratuit de 6 mois"

    body = f"""Bonjour,

Merci de vous être inscrit à ArkWatch!

Vous faites partie des 10 premiers utilisateurs à bénéficier de 6 mois d'essai GRATUIT - aucune carte bancaire requise.

=== PROCHAINES ÉTAPES ===

1. Activez votre compte: https://watch.arkforge.fr/register.html
2. Créez votre API key
3. Configurez votre première surveillance

=== POURQUOI ARKWATCH? ===

🔍 Surveillez n'importe quelle page web
🤖 Intelligence artificielle intégrée
📧 Alertes par email en temps réel
⏱️ Intervalles personnalisables

=== BESOIN D'AIDE? ===

📚 Documentation: https://arkforge.fr/docs
💬 Support: contact@arkforge.fr

Votre période d'essai commence aujourd'hui et se termine le {(datetime.utcnow() + timedelta(days=TRIAL_DURATION_DAYS)).strftime("%Y-%m-%d")}.

À très vite sur ArkWatch!

L'équipe ArkWatch
---
https://arkforge.fr
Se désinscrire: https://watch.arkforge.fr/api/unsubscribe?email={email}
"""

    success = send_email(email, subject, body)
    if success:
        update_nurture_log(email, "welcome_sent", {"phase": "signup"})
    return success


def send_activation_reminder(email: str, days_since_signup: int) -> bool:
    """Send activation reminder (Phase 2: Activation, J+1-3)."""
    subject = "🚀 Activez votre compte ArkWatch en 2 minutes"

    body = f"""Bonjour,

Nous avons remarqué que vous ne vous êtes pas encore connecté à ArkWatch.

Votre essai gratuit de 6 mois est déjà actif! Ne perdez pas de temps.

=== ACTIVATION RAPIDE (2 MIN) ===

1. Rendez-vous sur https://watch.arkforge.fr/register.html
2. Créez votre compte avec {email}
3. Générez votre API key
4. Configurez votre première surveillance

=== EXEMPLE D'UTILISATION ===

Surveillez:
- Le site d'un concurrent
- Une page de prix
- Un blog pour les nouveaux articles
- Une page de documentation technique

L'IA analyse les changements et vous alerte uniquement sur ce qui compte.

=== BESOIN D'AIDE? ===

Répondez à cet email, nous sommes là pour vous aider!

Il vous reste {180 - days_since_signup} jours d'essai gratuit.

L'équipe ArkWatch
---
https://arkforge.fr
Se désinscrire: https://watch.arkforge.fr/api/unsubscribe?email={email}
"""

    success = send_email(email, subject, body)
    if success:
        update_nurture_log(email, "activation_reminder_sent", {
            "phase": "activation",
            "days_since_signup": days_since_signup
        })
    return success


def send_engagement_tips(email: str, days_since_signup: int) -> bool:
    """Send engagement tips (Phase 3: Engagement, J+7-14)."""
    subject = "💡 3 astuces pour tirer le maximum d'ArkWatch"

    body = f"""Bonjour,

Vous utilisez ArkWatch depuis {days_since_signup} jours. Voici 3 astuces pour aller plus loin:

=== ASTUCE #1: INTERVALLES INTELLIGENTS ===

- Pages statiques (CGV, mentions légales): 1x/semaine
- Pages dynamiques (blog, actualités): 1x/jour
- Pages critiques (prix, stock): 1x/heure

=== ASTUCE #2: SEUILS DE CHANGEMENT ===

Configurez min_change_ratio pour filtrer les petits changements:
- 0.01 = très sensible (1% de changement)
- 0.05 = équilibré (5% de changement)
- 0.10 = conservateur (10% de changement)

=== ASTUCE #3: UTILISEZ L'IA ===

Notre IA analyse chaque changement et:
- Résume les modifications
- Évalue l'importance (low/medium/high/critical)
- Génère un diff lisible

=== EXEMPLES D'UTILISATION ===

✅ Veille concurrentielle (nouvelles fonctionnalités)
✅ Monitoring de prix (changements tarifaires)
✅ Conformité légale (modifications CGV/RGPD)
✅ Veille technologique (nouvelles versions)

Besoin d'aide? Répondez à cet email!

L'équipe ArkWatch
---
https://arkforge.fr
Se désinscrire: https://watch.arkforge.fr/api/unsubscribe?email={email}
"""

    success = send_email(email, subject, body)
    if success:
        update_nurture_log(email, "engagement_tips_sent", {
            "phase": "engagement",
            "days_since_signup": days_since_signup
        })
    return success


def send_conversion_reminder(email: str, days_since_signup: int) -> bool:
    """Send conversion reminder (Phase 4: Conversion, J+150+)."""
    days_remaining = TRIAL_DURATION_DAYS - days_since_signup

    subject = f"⏰ Plus que {days_remaining} jours d'essai gratuit ArkWatch"

    body = f"""Bonjour,

Votre période d'essai gratuit de 6 mois touche à sa fin dans {days_remaining} jours.

=== RÉCAPITULATIF DE VOTRE ESSAI ===

📅 Inscrit depuis: {days_since_signup} jours
⏰ Fin de l'essai: {(datetime.utcnow() + timedelta(days=days_remaining)).strftime("%Y-%m-%d")}
🎁 Essai gratuit: 6 mois complets

=== CONTINUEZ AVEC ARKWATCH ===

Pour continuer à bénéficier d'ArkWatch, choisissez votre formule:

💼 STARTER (9€/mois)
- 5 surveillances actives
- Vérifications jusqu'à 1x/heure
- IA + alertes email

🚀 PRO (29€/mois)
- 20 surveillances actives
- Vérifications jusqu'à 15 min
- Tout STARTER + support prioritaire

🏢 BUSINESS (99€/mois)
- Surveillances illimitées
- Vérifications jusqu'à 5 min
- Tout PRO + SLA 99.9%

👉 Choisissez votre formule: https://watch.arkforge.fr/pricing.html

=== QUESTIONS FRÉQUENTES ===

Q: Que se passe-t-il à la fin de l'essai?
R: Vos surveillances seront mises en pause. Vous pourrez les réactiver en souscrivant.

Q: Puis-je garder mes données?
R: Oui, toutes vos surveillances et historiques sont conservés.

Q: Puis-je annuler à tout moment?
R: Oui, sans engagement, annulation en 1 clic.

=== BESOIN D'AIDE? ===

Répondez à cet email ou contactez-nous: contact@arkforge.fr

Merci d'avoir testé ArkWatch!

L'équipe ArkWatch
---
https://arkforge.fr
Se désinscrire: https://watch.arkforge.fr/api/unsubscribe?email={email}
"""

    success = send_email(email, subject, body)
    if success:
        update_nurture_log(email, "conversion_reminder_sent", {
            "phase": "conversion",
            "days_since_signup": days_since_signup,
            "days_remaining": days_remaining
        })
    return success


def process_signup(signup: dict[str, Any]) -> dict[str, str]:
    """Process a single signup and determine action."""
    email = signup.get("email", "")
    registered_at_str = signup.get("registered_at", "")

    if not email or not registered_at_str:
        return {"action": "skip", "reason": "missing_data"}

    try:
        registered_at = datetime.fromisoformat(registered_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return {"action": "skip", "reason": "invalid_date"}

    now = datetime.utcnow()
    days_since_signup = (now - registered_at).days

    # Check if trial expired
    if days_since_signup > TRIAL_DURATION_DAYS:
        return {"action": "skip", "reason": "trial_expired"}

    # Get nurture history
    nurture_log = get_nurture_log(email)
    events = nurture_log.get("events", [])
    sent_events = {event["type"] for event in events}

    # Check account status
    has_account = has_activated_account(email)
    has_watches = has_created_watches(email)

    # Phase 1: Welcome (J+0, sent once)
    if "welcome_sent" not in sent_events:
        send_welcome_email(email, signup)
        return {"action": "welcome_sent", "phase": "signup"}

    # Phase 2: Activation reminder (J+2, if not activated)
    if days_since_signup >= 2 and not has_account and "activation_reminder_sent" not in sent_events:
        send_activation_reminder(email, days_since_signup)
        return {"action": "activation_reminder_sent", "phase": "activation"}

    # Phase 3: Engagement tips (J+7, if activated but no watches)
    if days_since_signup >= 7 and has_account and not has_watches and "engagement_tips_sent" not in sent_events:
        send_engagement_tips(email, days_since_signup)
        return {"action": "engagement_tips_sent", "phase": "engagement"}

    # Phase 4: Conversion reminder (J+150, J+165, J+175)
    conversion_days = [150, 165, 175]
    for reminder_day in conversion_days:
        if days_since_signup >= reminder_day:
            event_key = f"conversion_reminder_sent_{reminder_day}"
            if event_key not in sent_events:
                send_conversion_reminder(email, days_since_signup)
                update_nurture_log(email, event_key, {"reminder_day": reminder_day})
                return {"action": event_key, "phase": "conversion"}

    return {"action": "skip", "reason": "no_action_needed"}


def main():
    """Main nurture process."""
    logger.info("=== Starting Free Trial Nurture Process ===")

    # Load signups
    signups = load_json(SIGNUPS_FILE)
    logger.info(f"Loaded {len(signups)} signups")

    if not signups:
        logger.warning("No signups found")
        return

    # Process each signup
    stats = {
        "total": len(signups),
        "welcome_sent": 0,
        "activation_reminder_sent": 0,
        "engagement_tips_sent": 0,
        "conversion_reminder_sent": 0,
        "skipped": 0,
        "errors": 0,
    }

    for signup in signups:
        try:
            result = process_signup(signup)
            action = result.get("action", "skip")

            if action == "skip":
                stats["skipped"] += 1
            elif "welcome" in action:
                stats["welcome_sent"] += 1
            elif "activation" in action:
                stats["activation_reminder_sent"] += 1
            elif "engagement" in action:
                stats["engagement_tips_sent"] += 1
            elif "conversion" in action:
                stats["conversion_reminder_sent"] += 1

            logger.info(f"Processed {signup.get('email')}: {action}")

        except Exception as e:
            logger.error(f"Error processing {signup.get('email')}: {e}")
            stats["errors"] += 1

    # Log summary
    logger.info("=== Nurture Process Summary ===")
    for key, value in stats.items():
        logger.info(f"{key}: {value}")

    logger.info("=== Nurture Process Completed ===")


if __name__ == "__main__":
    main()
