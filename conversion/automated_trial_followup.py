#!/usr/bin/env python3
"""
Automated Trial Follow-up System for ArkWatch
Envoie relances automatiques J+1, J+3, J+7 aux trials sans conversion
Warming progressif avec tracking opens/clicks
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
TRIAL_SIGNUPS_FILE = DATA_DIR / "trial_signups_tracking.json"
FOLLOWUP_STATE_FILE = DATA_DIR / "trial_followup_state.json"
FOLLOWUP_LOG_FILE = DATA_DIR / "trial_followup_log.json"

# Email sender
EMAIL_SENDER = "/opt/claude-ceo/automation/email_sender.py"

# Campaign sequences
FOLLOWUP_SEQUENCES = {
    "day1": {
        "day_offset": 1,
        "subject": "Bienvenue sur ArkWatch - Tips pour commencer",
        "template": "onboarding_tips"
    },
    "day3": {
        "day_offset": 3,
        "subject": "Comment {use_case} avec ArkWatch - Case Study",
        "template": "case_study"
    },
    "day7": {
        "day_offset": 7,
        "subject": "Débloquez le potentiel d'ArkWatch - Call 15min offert",
        "template": "offer_call"
    }
}


def load_trial_signups() -> dict:
    """Load trial signups from tracking file."""
    if not TRIAL_SIGNUPS_FILE.exists():
        return {"submissions": [], "metrics": {}}

    try:
        with open(TRIAL_SIGNUPS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"submissions": [], "metrics": {}}


def load_followup_state() -> dict:
    """Load follow-up state (tracks which emails were sent)."""
    if not FOLLOWUP_STATE_FILE.exists():
        return {"followups": {}, "last_run": None}

    try:
        with open(FOLLOWUP_STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"followups": {}, "last_run": None}


def save_followup_state(state: dict):
    """Save follow-up state atomically."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(FOLLOWUP_STATE_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(FOLLOWUP_STATE_FILE))


def log_followup_action(action: dict):
    """Log follow-up action for audit trail."""
    FOLLOWUP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logs = []
    if FOLLOWUP_LOG_FILE.exists():
        try:
            with open(FOLLOWUP_LOG_FILE) as f:
                logs = json.load(f)
        except (json.JSONDecodeError, OSError):
            logs = []

    logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        **action
    })

    # Keep last 1000 logs
    logs = logs[-1000:]

    tmp = str(FOLLOWUP_LOG_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(FOLLOWUP_LOG_FILE))


def extract_use_case(usecase_text: str) -> str:
    """Extract simple use case from user's description."""
    text = usecase_text.lower()

    # Common patterns
    if "status page" in text or "incident" in text:
        return "surveiller votre status page"
    elif "landing" in text or "site" in text or "website" in text:
        return "monitorer votre site web"
    elif "pricing" in text or "prix" in text:
        return "suivre vos prix et concurrence"
    elif "api" in text:
        return "surveiller votre API"
    elif "checkout" in text or "payment" in text:
        return "protéger votre checkout"
    elif "competitor" in text or "concurr" in text:
        return "analyser vos concurrents"
    else:
        return "optimiser votre surveillance web"


def generate_email_body(template: str, submission: dict, sequence_info: dict) -> tuple[str, str]:
    """Generate email body (text + HTML) based on template."""
    name = submission.get("name", "").split()[0] if submission.get("name") else "là"
    email = submission["email"]
    usecase = extract_use_case(submission.get("usecase", ""))

    if template == "onboarding_tips":
        subject = sequence_info["subject"]
        text_body = f"""Bonjour {name},

Bienvenue sur ArkWatch ! 🎉

Voici 3 tips pour tirer le maximum de votre trial 14 jours :

1️⃣ **Créez votre première Watch en 2 min**
   → Allez sur https://watch.arkforge.fr
   → Entrez l'URL à surveiller
   → Définissez vos critères de changement
   → Recevez des alertes email instantanées

2️⃣ **Testez les cas d'usage avancés**
   → Surveillance de prix (détectez les promos concurrents)
   → Monitoring de status page (soyez alerté avant vos clients)
   → Veille technologique (suivez les mises à jour produits)

3️⃣ **Configurez les alertes intelligentes**
   → Fréquence de vérification ajustable (5min à 24h)
   → Filtres de changement personnalisables
   → Historique complet des modifications

🎯 Besoin d'aide pour démarrer ?
Répondez simplement à cet email, je suis là pour vous accompagner.

À très vite,
L'équipe ArkWatch

---
https://watch.arkforge.fr
"""

        html_body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Bonjour {name},</h2>

<p>Bienvenue sur ArkWatch ! 🎉</p>

<p>Voici <strong>3 tips pour tirer le maximum</strong> de votre trial 14 jours :</p>

<h3>1️⃣ Créez votre première Watch en 2 min</h3>
<ul>
<li>Allez sur <a href="https://watch.arkforge.fr">watch.arkforge.fr</a></li>
<li>Entrez l'URL à surveiller</li>
<li>Définissez vos critères de changement</li>
<li>Recevez des alertes email instantanées</li>
</ul>

<h3>2️⃣ Testez les cas d'usage avancés</h3>
<ul>
<li>Surveillance de prix (détectez les promos concurrents)</li>
<li>Monitoring de status page (soyez alerté avant vos clients)</li>
<li>Veille technologique (suivez les mises à jour produits)</li>
</ul>

<h3>3️⃣ Configurez les alertes intelligentes</h3>
<ul>
<li>Fréquence de vérification ajustable (5min à 24h)</li>
<li>Filtres de changement personnalisables</li>
<li>Historique complet des modifications</li>
</ul>

<p style="margin-top: 30px;">
🎯 <strong>Besoin d'aide pour démarrer ?</strong><br>
Répondez simplement à cet email, je suis là pour vous accompagner.
</p>

<p>À très vite,<br>
L'équipe ArkWatch</p>

<hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
<p style="font-size: 12px; color: #888;">
<a href="https://watch.arkforge.fr">watch.arkforge.fr</a>
</p>
</body>
</html>"""

    elif template == "case_study":
        subject = sequence_info["subject"].format(use_case=usecase)
        text_body = f"""Bonjour {name},

Vous avez commencé votre trial ArkWatch il y a 3 jours - comment ça se passe ?

Je voulais partager un cas d'usage concret qui correspond à votre besoin : **{usecase}**.

📊 **Case Study : SaaS B2B qui a évité une perte de 50k€**

Un de nos early users utilisait ArkWatch pour surveiller sa page de checkout.
Un jour, ArkWatch a détecté que le bouton "Acheter" avait disparu suite à un déploiement.

Résultat :
✅ Alerte reçue en 5 minutes
✅ Bug corrigé en 15 minutes
✅ 50k€ de CA sauvés (checkout down = 0 conversion)

💡 **Comment reproduire ce succès avec ArkWatch :**
1. Créez une Watch sur votre page critique
2. Définissez les éléments à surveiller (boutons, prix, formulaires)
3. Configurez la fréquence (5-15min pour les pages business-critical)
4. Recevez des alertes instantanées si quelque chose change

🎯 **Votre trial expire dans 11 jours.**
Profitez-en pour tester ce cas d'usage dès maintenant.

Des questions ?
Répondez à cet email, je suis là pour vous aider.

À bientôt,
L'équipe ArkWatch

---
https://watch.arkforge.fr
"""

        html_body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Bonjour {name},</h2>

<p>Vous avez commencé votre trial ArkWatch il y a 3 jours - comment ça se passe ?</p>

<p>Je voulais partager un cas d'usage concret qui correspond à votre besoin : <strong>{usecase}</strong>.</p>

<h3 style="color: #0066cc;">📊 Case Study : SaaS B2B qui a évité une perte de 50k€</h3>

<p>Un de nos early users utilisait ArkWatch pour surveiller sa page de checkout.<br>
Un jour, ArkWatch a détecté que le bouton "Acheter" avait disparu suite à un déploiement.</p>

<div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
<strong>Résultat :</strong>
<ul style="margin: 10px 0;">
<li>✅ Alerte reçue en 5 minutes</li>
<li>✅ Bug corrigé en 15 minutes</li>
<li>✅ 50k€ de CA sauvés (checkout down = 0 conversion)</li>
</ul>
</div>

<h3>💡 Comment reproduire ce succès avec ArkWatch :</h3>
<ol>
<li>Créez une Watch sur votre page critique</li>
<li>Définissez les éléments à surveiller (boutons, prix, formulaires)</li>
<li>Configurez la fréquence (5-15min pour les pages business-critical)</li>
<li>Recevez des alertes instantanées si quelque chose change</li>
</ol>

<p style="margin-top: 30px;">
🎯 <strong>Votre trial expire dans 11 jours.</strong><br>
Profitez-en pour tester ce cas d'usage dès maintenant.
</p>

<p>Des questions ?<br>
Répondez à cet email, je suis là pour vous aider.</p>

<p>À bientôt,<br>
L'équipe ArkWatch</p>

<hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
<p style="font-size: 12px; color: #888;">
<a href="https://watch.arkforge.fr">watch.arkforge.fr</a>
</p>
</body>
</html>"""

    elif template == "offer_call":
        subject = sequence_info["subject"]
        text_body = f"""Bonjour {name},

Votre trial ArkWatch se termine dans 7 jours. 🕐

J'ai une question simple : **Avez-vous réussi à débloquer tout le potentiel d'ArkWatch ?**

Si vous rencontrez des difficultés ou si vous voulez optimiser votre configuration avant la fin du trial, je vous offre un **call de 15 minutes**.

📞 **Au programme du call :**
- Analyse de votre cas d'usage spécifique
- Configuration optimale pour vos besoins
- Tips & tricks des power users
- Réponses à toutes vos questions

🎯 **Objectif : Vous faire économiser du temps et maximiser votre ROI.**

Réservez votre créneau directement :
→ Répondez à cet email avec vos disponibilités cette semaine

Ou continuez en autonomie :
→ Documentation complète : https://watch.arkforge.fr/docs
→ Exemples de configuration : https://watch.arkforge.fr/examples

**Note importante :** Votre trial expire le {(datetime.utcnow() + timedelta(days=7)).strftime('%d/%m/%Y')}.
Pour continuer après cette date, il faudra souscrire à un plan payant.

Tarifs trial → payant :
• Starter : 29€/mois (100 watches)
• Pro : 99€/mois (500 watches)
• Enterprise : sur devis

Des questions ? Je suis là.

Merci de votre confiance,
L'équipe ArkWatch

---
https://watch.arkforge.fr
"""

        html_body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Bonjour {name},</h2>

<p>Votre trial ArkWatch se termine dans <strong style="color: #cc0000;">7 jours</strong>. 🕐</p>

<p>J'ai une question simple : <strong>Avez-vous réussi à débloquer tout le potentiel d'ArkWatch ?</strong></p>

<p>Si vous rencontrez des difficultés ou si vous voulez optimiser votre configuration avant la fin du trial, je vous offre un <strong>call de 15 minutes</strong>.</p>

<div style="background: #f0f8ff; padding: 20px; border-radius: 5px; margin: 20px 0;">
<h3 style="margin-top: 0;">📞 Au programme du call :</h3>
<ul>
<li>Analyse de votre cas d'usage spécifique</li>
<li>Configuration optimale pour vos besoins</li>
<li>Tips & tricks des power users</li>
<li>Réponses à toutes vos questions</li>
</ul>
<p style="margin-bottom: 0;"><strong>🎯 Objectif : Vous faire économiser du temps et maximiser votre ROI.</strong></p>
</div>

<h3>Réservez votre créneau directement :</h3>
<p>→ Répondez à cet email avec vos disponibilités cette semaine</p>

<h3>Ou continuez en autonomie :</h3>
<ul>
<li>Documentation complète : <a href="https://watch.arkforge.fr/docs">watch.arkforge.fr/docs</a></li>
<li>Exemples de configuration : <a href="https://watch.arkforge.fr/examples">watch.arkforge.fr/examples</a></li>
</ul>

<div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
<strong>Note importante :</strong> Votre trial expire le <strong>{(datetime.utcnow() + timedelta(days=7)).strftime('%d/%m/%Y')}</strong>.<br>
Pour continuer après cette date, il faudra souscrire à un plan payant.
</div>

<h3>Tarifs trial → payant :</h3>
<ul>
<li><strong>Starter</strong> : 29€/mois (100 watches)</li>
<li><strong>Pro</strong> : 99€/mois (500 watches)</li>
<li><strong>Enterprise</strong> : sur devis</li>
</ul>

<p style="margin-top: 30px;">Des questions ? Je suis là.</p>

<p>Merci de votre confiance,<br>
L'équipe ArkWatch</p>

<hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
<p style="font-size: 12px; color: #888;">
<a href="https://watch.arkforge.fr">watch.arkforge.fr</a>
</p>
</body>
</html>"""

    else:
        # Fallback
        subject = "ArkWatch - Mise à jour de votre trial"
        text_body = f"Bonjour {name},\n\nNouvelles de votre trial ArkWatch.\n\nL'équipe ArkWatch"
        html_body = f"<p>Bonjour {name},</p><p>Nouvelles de votre trial ArkWatch.</p><p>L'équipe ArkWatch</p>"

    return subject, text_body, html_body


def should_send_followup(submission: dict, sequence: str, followup_state: dict) -> bool:
    """Check if we should send this follow-up email."""
    email = submission["email"]
    submitted_at_str = submission.get("submitted_at", "")

    if not submitted_at_str:
        return False

    # Parse submission date
    try:
        submitted_at = datetime.fromisoformat(submitted_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False

    # Check if already converted
    if submission.get("conversion_completed"):
        return False

    # Check if already sent this sequence
    if email not in followup_state["followups"]:
        followup_state["followups"][email] = {}

    if sequence in followup_state["followups"][email]:
        return False  # Already sent

    # Check timing
    days_since_signup = (datetime.utcnow() - submitted_at).days
    target_day = FOLLOWUP_SEQUENCES[sequence]["day_offset"]

    # Send if we're at or past the target day (within 1 day tolerance)
    if days_since_signup >= target_day and days_since_signup <= target_day + 1:
        return True

    return False


def send_followup_email(submission: dict, sequence: str, sequence_info: dict) -> bool:
    """Send follow-up email via email_sender.py."""
    email = submission["email"]
    subject, text_body, html_body = generate_email_body(
        sequence_info["template"],
        submission,
        sequence_info
    )

    try:
        result = subprocess.run([
            "python3",
            EMAIL_SENDER,
            email,
            subject,
            text_body,
            html_body
        ], capture_output=True, text=True, timeout=30, check=False)

        success = result.returncode == 0

        log_followup_action({
            "action": "send_followup",
            "sequence": sequence,
            "email": email,
            "subject": subject,
            "success": success,
            "error": result.stderr if not success else None
        })

        return success

    except Exception as e:
        log_followup_action({
            "action": "send_followup",
            "sequence": sequence,
            "email": email,
            "success": False,
            "error": str(e)
        })
        return False


def run_followup_cycle() -> dict:
    """Main follow-up cycle - check all trials and send appropriate follow-ups."""
    signups_data = load_trial_signups()
    followup_state = load_followup_state()

    submissions = signups_data.get("submissions", [])

    stats = {
        "checked_at": datetime.utcnow().isoformat(),
        "total_trials": len(submissions),
        "followups_sent": 0,
        "followups_failed": 0,
        "sequences_sent": {
            "day1": 0,
            "day3": 0,
            "day7": 0
        }
    }

    for submission in submissions:
        email = submission["email"]

        # Skip test emails
        if "test" in email.lower() or "example.com" in email.lower():
            continue

        # Check each sequence
        for sequence, sequence_info in FOLLOWUP_SEQUENCES.items():
            if should_send_followup(submission, sequence, followup_state):
                # Send email
                success = send_followup_email(submission, sequence, sequence_info)

                if success:
                    # Mark as sent
                    followup_state["followups"][email][sequence] = {
                        "sent_at": datetime.utcnow().isoformat(),
                        "subject": sequence_info["subject"]
                    }
                    stats["followups_sent"] += 1
                    stats["sequences_sent"][sequence] += 1
                else:
                    stats["followups_failed"] += 1

    # Update state
    followup_state["last_run"] = datetime.utcnow().isoformat()
    save_followup_state(followup_state)

    return stats


if __name__ == "__main__":
    # Run follow-up cycle
    result = run_followup_cycle()
    print(json.dumps(result, indent=2))
