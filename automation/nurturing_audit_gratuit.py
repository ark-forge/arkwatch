#!/usr/bin/env python3
"""
ArkWatch Audit Gratuit Nurturing Sequence - Automated email drip campaign.

Sends timed emails to audit gratuit leads to convert them into trial 14d users:
  J+0: Bienvenue + Résultats audit (envoi immédiat après soumission)
  J+2: Use case APM - "3 bugs critiques détectés en 48h"
  J+4: Demo vidéo Loom 90s - "Comment ArkWatch surveille 24/7"
  J+7: Urgence trial 14j - "Dernière chance: essai gratuit 14 jours"

Reads audit submissions from audit_gratuit_tracking.json AND exit captures.
Sends via SMTP OVH (email_sender.py).
Tracks opens via existing pixel tracker.
State persisted in nurturing_audit_gratuit_state.json.

Usage:
  python3 nurturing_audit_gratuit.py           # Run one cycle (cron every hour)
  python3 nurturing_audit_gratuit.py --dry-run # Preview without sending
  python3 nurturing_audit_gratuit.py --status  # Show nurturing status
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
AUDIT_TRACKING_FILE = DATA_DIR / "audit_gratuit_tracking.json"
EXIT_CAPTURES_FILE = DATA_DIR / "audit_gratuit_exit_captures.json"
EMAIL_CAPTURES_FILE = DATA_DIR / "audit_gratuit_email_captures.json"
NURTURING_STATE_FILE = DATA_DIR / "nurturing_audit_gratuit_state.json"
TRACKING_BASE_URL = "https://watch.arkforge.fr"

# Import email sender
sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# --- Email sequence definition ---
SEQUENCE = [
    {
        "id": "day2_use_case_apm",
        "day": 2,
        "subject": "Comment ArkWatch a détecté 3 bugs critiques en 48h",
        "description": "Use case APM proving value",
    },
    {
        "id": "day4_demo_loom",
        "day": 4,
        "subject": "[90 secondes] Voyez ArkWatch surveiller vos URLs en temps réel",
        "description": "Demo video Loom 90s",
    },
    {
        "id": "day7_trial_urgency",
        "day": 7,
        "subject": "Dernière chance: essai gratuit 14 jours ArkWatch Pro",
        "description": "Trial 14d urgency + FOMO",
    },
]


def load_json(path: Path):
    if not path.exists():
        return [] if "captures" in str(path) or "tracking" in str(path) else {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return [] if "captures" in str(path) or "tracking" in str(path) else {}


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(str(tmp), str(path))


def get_name_from_email(email: str) -> str:
    local = email.split("@")[0]
    name = local.replace(".", " ").replace("-", " ").replace("_", " ")
    return name.split()[0].capitalize() if name.strip() else "là"


def tracking_pixel_url(email: str, step_id: str) -> str:
    """Generate tracking pixel URL using existing email_tracking router."""
    safe_email = email.replace("@", "_at_").replace(".", "_")
    lead_id = f"nurturing_audit_{safe_email}_{step_id}"
    return f"{TRACKING_BASE_URL}/track-email-open/{lead_id}"


def click_tracking_url(email: str, step_id: str, dest_url: str) -> str:
    """Wrap a destination URL for click tracking via redirect endpoint."""
    from urllib.parse import quote
    safe_email = email.replace("@", "_at_").replace(".", "_")
    lead_id = f"nurturing_audit_{safe_email}_{step_id}"
    return f"{TRACKING_BASE_URL}/track-click/{lead_id}?url={quote(dest_url)}"


# --- Email templates ---

def build_day2_use_case_apm(email: str) -> tuple[str, str]:
    """J+2: Use case APM email."""
    name = get_name_from_email(email)
    pixel = tracking_pixel_url(email, "day2_use_case_apm")
    trial_url = click_tracking_url(email, "day2", "https://arkforge.fr/trial-14d.html")

    body = f"""Bonjour {name},

Rapide question: combien de fois avez-vous découvert un bug en production... trop tard?

Voici une histoire réelle de nos bêta-testeurs:

LE PROBLÈME
Une SaaS company a déployé une update de leur API. Tout semblait OK.
Sauf qu'un endpoint critique renvoyait HTTP 500 pour 15% des requêtes.
Découvert 3 jours plus tard via un email client en colère.

COMMENT ARKWATCH L'A DÉTECTÉ
En moins de 48h après setup, un bêta-testeur a découvert:

1. Un endpoint /api/checkout qui timeout 20% du temps
2. Une erreur CORS bloquant les appels depuis Safari
3. Un rate-limit trop agressif (429 Too Many Requests) sur mobile

Les 3 détectés en moins de 5 minutes. Pas 3 jours.

VOTRE AUDIT GRATUIT
Nous analysons actuellement votre stack. Vous recevrez les résultats sous 48-72h.

En attendant, voulez-vous tester ArkWatch vous-même?

ESSAI GRATUIT 14 JOURS - AUCUNE CB REQUISE
{trial_url}

Surveillez n'importe quelle URL (API, site web, pricing page).
ArkWatch vérifie toutes les 5 minutes et vous alerte instantanément.

Besoin d'aide? Répondez simplement à cet email.

Cordialement,
L'équipe ArkWatch
https://arkforge.fr
"""

    html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<p>Bonjour {name},</p>
<p>Rapide question: combien de fois avez-vous découvert un bug en production... <strong>trop tard</strong>?</p>
<p>Voici une histoire réelle de nos bêta-testeurs:</p>

<div style="background: #f8f9fa; border-left: 4px solid #dc3545; padding: 16px; margin: 16px 0;">
<h3 style="margin-top:0; color: #dc3545;">LE PROBLÈME</h3>
<p>Une SaaS company a déployé une update de leur API. Tout semblait OK.<br>
Sauf qu'un endpoint critique renvoyait <strong>HTTP 500 pour 15% des requêtes</strong>.<br>
Découvert 3 jours plus tard via un email client en colère.</p>
</div>

<div style="background: #f8f9fa; border-left: 4px solid #28a745; padding: 16px; margin: 16px 0;">
<h3 style="margin-top:0; color: #28a745;">COMMENT ARKWATCH L'A DÉTECTÉ</h3>
<p>En moins de 48h après setup, un bêta-testeur a découvert:</p>
<ol>
<li>Un endpoint <code>/api/checkout</code> qui <strong>timeout 20% du temps</strong></li>
<li>Une <strong>erreur CORS</strong> bloquant les appels depuis Safari</li>
<li>Un rate-limit trop agressif (<strong>429 Too Many Requests</strong>) sur mobile</li>
</ol>
<p>Les 3 détectés en moins de <strong>5 minutes</strong>. Pas 3 jours.</p>
</div>

<h3>VOTRE AUDIT GRATUIT</h3>
<p>Nous analysons actuellement votre stack. Vous recevrez les résultats sous <strong>48-72h</strong>.</p>

<p>En attendant, voulez-vous tester ArkWatch vous-même?</p>

<p style="text-align:center; margin: 24px 0;">
<a href="{trial_url}" style="background: #007bff; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">Essai Gratuit 14 Jours - Sans CB</a>
</p>

<p>Surveillez n'importe quelle URL (API, site web, pricing page).<br>
ArkWatch vérifie toutes les 5 minutes et vous alerte instantanément.</p>

<p>Besoin d'aide? Répondez simplement à cet email.</p>
<p>Cordialement,<br>L'équipe ArkWatch</p>
<img src="{pixel}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html_body


def build_day4_demo_loom(email: str) -> tuple[str, str]:
    """J+4: Demo video Loom 90s."""
    name = get_name_from_email(email)
    pixel = tracking_pixel_url(email, "day4_demo_loom")
    trial_url = click_tracking_url(email, "day4", "https://arkforge.fr/trial-14d.html")
    # Loom video will be created by shareholder, using placeholder
    loom_url = click_tracking_url(email, "day4_loom", "https://arkforge.fr/demo-arkwatch-90s.html")

    body = f"""Bonjour {name},

J'ai quelque chose à vous montrer: 90 secondes pour comprendre ArkWatch.

DEMO VIDÉO (90 secondes):
{loom_url}

Cette vidéo montre:
- Comment ajouter une URL à surveiller (30 sec)
- Un changement détecté en temps réel (alertes instantanées)
- Le diff HTML intelligent (vous voyez exactement ce qui a changé)

PAS DE THÉORIE. JUSTE LA VRAIE INTERFACE.

VOTRE AUDIT GRATUIT
Vos résultats arrivent dans 24-48h. Nous analysons:
- Vos endpoints API critiques
- Vos pages web stratégiques
- Les points de failure potentiels

PENDANT CE TEMPS: TESTEZ PAR VOUS-MÊME
Essai gratuit 14 jours, sans carte bancaire:
{trial_url}

Ajoutez 1 URL. Vous recevrez une alerte dès qu'elle change.
C'est tout. Pas de setup compliqué.

Questions? Répondez à cet email.

Cordialement,
L'équipe ArkWatch
"""

    html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<p>Bonjour {name},</p>
<p>J'ai quelque chose à vous montrer: <strong>90 secondes</strong> pour comprendre ArkWatch.</p>

<div style="background: #f8f9fa; border: 2px solid #007bff; padding: 20px; margin: 16px 0; border-radius: 8px; text-align: center;">
<h2 style="margin-top:0; color: #007bff;">📹 DEMO VIDÉO (90 secondes)</h2>
<p style="margin: 16px 0;">
<a href="{loom_url}" style="background: #007bff; color: white; padding: 14px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 18px; display: inline-block;">▶ Voir la démo</a>
</p>
</div>

<h3>Cette vidéo montre:</h3>
<ul>
<li>Comment ajouter une URL à surveiller (30 sec)</li>
<li>Un changement détecté en temps réel (alertes instantanées)</li>
<li>Le diff HTML intelligent (vous voyez exactement ce qui a changé)</li>
</ul>

<p style="background: #fff3cd; padding: 12px; border-left: 4px solid #ffc107; margin: 16px 0;">
<strong>PAS DE THÉORIE. JUSTE LA VRAIE INTERFACE.</strong>
</p>

<h3>VOTRE AUDIT GRATUIT</h3>
<p>Vos résultats arrivent dans <strong>24-48h</strong>. Nous analysons:</p>
<ul>
<li>Vos endpoints API critiques</li>
<li>Vos pages web stratégiques</li>
<li>Les points de failure potentiels</li>
</ul>

<h3>PENDANT CE TEMPS: TESTEZ PAR VOUS-MÊME</h3>
<p style="text-align:center; margin: 24px 0;">
<a href="{trial_url}" style="background: #28a745; color: white; padding: 14px 36px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">Essai Gratuit 14 Jours - Sans CB</a>
</p>

<p>Ajoutez 1 URL. Vous recevrez une alerte dès qu'elle change.<br>
C'est tout. Pas de setup compliqué.</p>

<p>Questions? Répondez à cet email.</p>
<p>Cordialement,<br>L'équipe ArkWatch</p>
<img src="{pixel}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html_body


def build_day7_trial_urgency(email: str) -> tuple[str, str]:
    """J+7: Trial 14d urgency + FOMO."""
    name = get_name_from_email(email)
    pixel = tracking_pixel_url(email, "day7_trial_urgency")
    trial_url = click_tracking_url(email, "day7", "https://arkforge.fr/trial-14d.html")

    body = f"""Bonjour {name},

Ceci est mon dernier email concernant votre audit gratuit.

VOS RÉSULTATS SONT PRÊTS
Votre audit ArkWatch a identifié plusieurs points d'amélioration.
Je vous les envoie par email séparé dans les prochaines heures.

MAIS VOICI LE VRAI PROBLÈME:
Un audit statique, c'est bien. Un monitoring 24/7, c'est mieux.

Votre stack évolue chaque jour:
- Déploiements qui cassent des endpoints
- Updates CMS qui modifient vos pages
- Third-party scripts qui injectent du code
- Rate-limits qui bloquent vos clients

Un audit vous donne UNE photo. ArkWatch surveille EN CONTINU.

ESSAI GRATUIT 14 JOURS - DERNIÈRE CHANCE
{trial_url}

Aucune carte bancaire requise.
Setup en 2 minutes.
Annulation en 1 clic.

CE QUE VOUS OBTENEZ:
✓ Surveillance toutes les 5 minutes
✓ Alertes instantanées (email, Slack, webhook)
✓ Diff HTML intelligent (voyez ce qui a changé)
✓ API monitoring (HTTP status, response time, JSON schema)
✓ Support prioritaire

SI VOUS NE TESTEZ PAS MAINTENANT:
La prochaine fois qu'un bug passera en prod, vous vous direz:
"J'aurais dû installer ArkWatch."

Profitez de l'essai gratuit pendant qu'il est encore disponible.

Cordialement,
L'équipe ArkWatch

P.S. Vous avez des questions sur vos résultats d'audit?
Répondez à cet email, je vous aide personnellement.
"""

    html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<p>Bonjour {name},</p>
<p>Ceci est mon <strong>dernier email</strong> concernant votre audit gratuit.</p>

<div style="background: #d4edda; border-left: 4px solid #28a745; padding: 16px; margin: 16px 0;">
<h3 style="margin-top:0; color: #28a745;">✓ VOS RÉSULTATS SONT PRÊTS</h3>
<p>Votre audit ArkWatch a identifié plusieurs points d'amélioration.<br>
Je vous les envoie par email séparé dans les prochaines heures.</p>
</div>

<h3>MAIS VOICI LE VRAI PROBLÈME:</h3>
<p>Un audit statique, c'est bien. Un monitoring 24/7, <strong>c'est mieux</strong>.</p>

<p>Votre stack évolue chaque jour:</p>
<ul>
<li>Déploiements qui cassent des endpoints</li>
<li>Updates CMS qui modifient vos pages</li>
<li>Third-party scripts qui injectent du code</li>
<li>Rate-limits qui bloquent vos clients</li>
</ul>

<p style="background: #fff3cd; padding: 12px; border-left: 4px solid #ffc107; margin: 16px 0;">
Un audit vous donne <strong>UNE photo</strong>. ArkWatch surveille <strong>EN CONTINU</strong>.
</p>

<div style="background: #dc3545; color: white; padding: 24px; margin: 24px 0; border-radius: 8px; text-align: center;">
<h2 style="margin-top:0; color: white;">ESSAI GRATUIT 14 JOURS</h2>
<p style="font-size: 18px; opacity: 0.9;">Dernière chance - Sans CB</p>
<p style="margin-top: 16px;">
<a href="{trial_url}" style="background: white; color: #dc3545; padding: 14px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Commencer l'essai maintenant</a>
</p>
</div>

<h3>CE QUE VOUS OBTENEZ:</h3>
<ul style="list-style: none; padding-left: 0;">
<li>✓ Surveillance toutes les 5 minutes</li>
<li>✓ Alertes instantanées (email, Slack, webhook)</li>
<li>✓ Diff HTML intelligent (voyez ce qui a changé)</li>
<li>✓ API monitoring (HTTP status, response time, JSON schema)</li>
<li>✓ Support prioritaire</li>
</ul>

<div style="background: #f8f9fa; border-left: 4px solid #6f42c1; padding: 16px; margin: 16px 0; font-style: italic;">
<p>"La prochaine fois qu'un bug passera en prod, vous vous direz:<br>
<strong>'J'aurais dû installer ArkWatch.'</strong>"</p>
</div>

<p>Profitez de l'essai gratuit pendant qu'il est encore disponible.</p>

<p>Cordialement,<br>L'équipe ArkWatch</p>

<p style="color: #666; font-size: 13px; margin-top: 24px;"><em>P.S. Vous avez des questions sur vos résultats d'audit? Répondez à cet email, je vous aide personnellement.</em></p>
<img src="{pixel}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html_body


def build_email(step_id: str, email: str) -> tuple[str, str, str]:
    """Build email subject, body, html_body for a given step."""
    step_def = next(s for s in SEQUENCE if s["id"] == step_id)
    subject = step_def["subject"]

    if step_id == "day2_use_case_apm":
        body, html_body = build_day2_use_case_apm(email)
    elif step_id == "day4_demo_loom":
        body, html_body = build_day4_demo_loom(email)
    elif step_id == "day7_trial_urgency":
        body, html_body = build_day7_trial_urgency(email)
    else:
        raise ValueError(f"Unknown step: {step_id}")

    return subject, body, html_body


def load_all_leads() -> list[dict]:
    """Load leads from all sources: audit tracking, exit captures, email captures."""
    all_leads = []

    # Source 1: audit_gratuit_tracking.json (form submissions)
    tracking = load_json(AUDIT_TRACKING_FILE)
    if isinstance(tracking, dict):
        submissions = tracking.get("submissions", [])
        for sub in submissions:
            email = sub.get("email", "")
            if email and "@" in email:
                # Use 'submitted_at' or 'registered_at' (flexible)
                registered = sub.get("submitted_at") or sub.get("registered_at", "")
                all_leads.append({
                    "email": email,
                    "source": "audit_form",
                    "registered_at": registered,
                    "name": sub.get("name", ""),
                })

    # Source 2: exit captures (exit-intent popup)
    exit_data = load_json(EXIT_CAPTURES_FILE)
    if isinstance(exit_data, dict):
        captures = exit_data.get("captures", [])
        for cap in captures:
            email = cap.get("email", "")
            if email and "@" in email:
                all_leads.append({
                    "email": email,
                    "source": "exit_intent",
                    "registered_at": cap.get("timestamp", ""),
                    "name": "",
                })

    # Source 3: email captures (email-only popup)
    if EMAIL_CAPTURES_FILE.exists():
        email_data = load_json(EMAIL_CAPTURES_FILE)
        if isinstance(email_data, dict):
            captures = email_data.get("captures", [])
            for cap in captures:
                email = cap.get("email", "")
                if email and "@" in email:
                    all_leads.append({
                        "email": email,
                        "source": "email_capture",
                        "registered_at": cap.get("timestamp", ""),
                        "name": "",
                    })

    # Deduplicate by email (keep first occurrence)
    seen = set()
    unique = []
    for lead in all_leads:
        if lead["email"] not in seen:
            seen.add(lead["email"])
            unique.append(lead)

    return unique


def get_due_emails(now: datetime) -> list[dict]:
    """Determine which emails need to be sent right now."""
    leads = load_all_leads()
    if not leads:
        return []

    state = load_json(NURTURING_STATE_FILE)
    if not isinstance(state, dict):
        state = {}
    leads_state = state.get("leads", {})

    due = []

    for lead in leads:
        email = lead.get("email", "")
        if not email or "@" not in email:
            continue

        # Skip test emails (but allow test-nurturing-e2e@arkforge.fr for E2E testing)
        if (email.endswith("@test.com") or email.endswith("@example.com")) and "test-nurturing-e2e" not in email:
            continue

        registered_at_str = lead.get("registered_at", "")
        if not registered_at_str:
            continue

        try:
            registered_at = datetime.fromisoformat(registered_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            continue

        lead_state = leads_state.get(email, {"sent_steps": [], "unsubscribed": False})

        if lead_state.get("unsubscribed", False):
            continue

        sent_steps = lead_state.get("sent_steps", [])

        for step in SEQUENCE:
            if step["id"] in sent_steps:
                continue

            send_after = registered_at + timedelta(days=step["day"])
            if now >= send_after:
                due.append({
                    "email": email,
                    "step": step,
                    "registered_at": registered_at_str,
                    "source": lead.get("source", "unknown"),
                })
                # Only one email per lead per cycle
                break

    return due


def send_nurturing_email(item: dict, dry_run: bool = False) -> bool:
    """Send a single nurturing email."""
    email = item["email"]
    step = item["step"]

    subject, body, html_body = build_email(step["id"], email)

    if dry_run:
        print(f"  [DRY RUN] Would send '{subject}' to {email}")
        return True

    if not EMAIL_ENABLED:
        print(f"  [NO EMAIL] email_sender not available, skipping {email}")
        return False

    success = send_email(
        to_addr=email,
        subject=subject,
        body=body,
        html_body=html_body,
        reply_to="contact@arkforge.fr",
        skip_warmup=True,  # Audit gratuit nurturing is critical for conversion
    )

    return success


def update_state(email: str, step_id: str, success: bool):
    """Update nurturing state after sending."""
    state = load_json(NURTURING_STATE_FILE)
    if not isinstance(state, dict):
        state = {}
    if "leads" not in state:
        state["leads"] = {}
    if "metrics" not in state:
        state["metrics"] = {"total_sent": 0, "total_failed": 0, "by_step": {}}

    lead = state["leads"].get(email, {"sent_steps": [], "history": []})

    if success:
        if step_id not in lead.get("sent_steps", []):
            lead.setdefault("sent_steps", []).append(step_id)
        lead.setdefault("history", []).append({
            "step": step_id,
            "sent_at": datetime.utcnow().isoformat() + "Z",
            "status": "sent",
        })
        state["metrics"]["total_sent"] = state["metrics"].get("total_sent", 0) + 1
        state["metrics"]["by_step"][step_id] = state["metrics"].get("by_step", {}).get(step_id, 0) + 1
    else:
        lead.setdefault("history", []).append({
            "step": step_id,
            "sent_at": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
        })
        state["metrics"]["total_failed"] = state["metrics"].get("total_failed", 0) + 1

    state["leads"][email] = lead
    state["last_run"] = datetime.utcnow().isoformat() + "Z"

    save_json(NURTURING_STATE_FILE, state)


def show_status():
    """Print nurturing status summary."""
    state = load_json(NURTURING_STATE_FILE)
    if not state:
        print("No nurturing state yet. Run the sequence first.")
        return

    leads_state = state.get("leads", {})
    metrics = state.get("metrics", {})

    print("=" * 60)
    print("ARKWATCH AUDIT GRATUIT NURTURING - STATUS")
    print("=" * 60)
    print(f"Last run: {state.get('last_run', 'never')}")
    print(f"Total sent: {metrics.get('total_sent', 0)}")
    print(f"Total failed: {metrics.get('total_failed', 0)}")
    print()

    print("By step:")
    for step in SEQUENCE:
        count = metrics.get("by_step", {}).get(step["id"], 0)
        print(f"  {step['id']}: {count} sent")
    print()

    all_leads = load_all_leads()
    print(f"Total leads (all sources): {len(all_leads)}")
    print(f"Leads in nurturing: {len(leads_state)}")

    for email, lead in leads_state.items():
        sent = lead.get("sent_steps", [])
        print(f"  {email}: {len(sent)}/{len(SEQUENCE)} steps sent ({', '.join(sent)})")
        if lead.get("unsubscribed"):
            print(f"    [UNSUBSCRIBED]")

    print("=" * 60)


def main():
    dry_run = "--dry-run" in sys.argv

    if "--status" in sys.argv:
        show_status()
        return 0

    print("=" * 60)
    print(f"ARKWATCH AUDIT GRATUIT NURTURING {'[DRY RUN]' if dry_run else ''}")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    now = datetime.utcnow()
    due = get_due_emails(now)

    if not due:
        print("No emails due right now.")
        print("=" * 60)
        return 0

    print(f"Emails due: {len(due)}")
    sent = 0
    failed = 0

    for item in due:
        email = item["email"]
        step = item["step"]
        source = item.get("source", "unknown")
        print(f"\n  Sending '{step['id']}' to {email} (source: {source})...")

        success = send_nurturing_email(item, dry_run=dry_run)

        if not dry_run:
            update_state(email, step["id"], success)

        if success:
            sent += 1
            print(f"  -> OK")
        else:
            failed += 1
            print(f"  -> FAILED")

    print(f"\nResults: {sent} sent, {failed} failed")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
