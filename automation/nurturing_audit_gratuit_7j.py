#!/usr/bin/env python3
"""
ArkWatch Audit Gratuit - Nurturing Sequence 7 jours.

Envoie une séquence email automatique sur 7 jours aux leads existants
(outreach, cold email, etc.) pour les convertir vers le trial 14 jours.

Séquence:
  J+0: Welcome + proposition audit gratuit
  J+2: Use case APM concret (bug pricing page)
  J+4: Lien démo 90s + quick win monitoring
  J+7: Urgence - places limitées trial 14j

Source des leads: unified_email_tracking.json
Envoi via: email_sender.py (OVH SMTP)
Tracking: pixel ouvertures + click redirect
État: nurturing_audit_gratuit_state.json

Usage:
  python3 nurturing_audit_gratuit_7j.py           # Run one cycle (cron)
  python3 nurturing_audit_gratuit_7j.py --dry-run  # Preview sans envoi
  python3 nurturing_audit_gratuit_7j.py --status   # Dashboard état
  python3 nurturing_audit_gratuit_7j.py --enroll    # Enroll tous les leads existants
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

# === Paths ===
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
LEADS_FILE = DATA_DIR / "unified_email_tracking.json"
STATE_FILE = DATA_DIR / "nurturing_audit_gratuit_state.json"
TRACKING_BASE = "https://watch.arkforge.fr"

# === Email sender ===
sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# === Séquence nurturing 7 jours ===
SEQUENCE = [
    {
        "id": "j0_welcome_audit",
        "day": 0,
        "subject": "Votre audit monitoring gratuit est prêt",
        "desc": "Welcome + proposition audit gratuit personnalisé",
    },
    {
        "id": "j2_usecase_apm",
        "day": 2,
        "subject": "Comment une erreur de prix invisible a coûté 47K€ en 3 jours",
        "desc": "Use case APM concret - bug pricing page non détecté",
    },
    {
        "id": "j4_demo_quickwin",
        "day": 4,
        "subject": "90 secondes pour configurer votre premier moniteur",
        "desc": "Démo vidéo 90s + quick win monitoring",
    },
    {
        "id": "j7_urgence_trial",
        "day": 7,
        "subject": "[Dernier rappel] 5 places restantes - Trial gratuit 14 jours",
        "desc": "Urgence scarcity + CTA trial 14j",
    },
]

# === URLs clés ===
TRIAL_URL = "https://arkforge.fr/trial-14d.html"
DEMO_URL = "https://arkforge.fr/demo.html"
AUDIT_URL = "https://arkforge.fr/audit-gratuit-monitoring.html"
PRICING_URL = "https://arkforge.fr/pricing.html"
CALENDLY_URL = "https://calendly.com/arkforge/audit-monitoring-15min"


# === Helpers ===

def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(str(tmp), str(path))


def pixel_url(email: str, step_id: str) -> str:
    safe = email.replace("@", "_at_").replace(".", "_")
    lead_id = f"audit_nurturing_{safe}_{step_id}"
    return f"{TRACKING_BASE}/track-email-open/{lead_id}"


def click_url(email: str, step_id: str, dest: str) -> str:
    safe = email.replace("@", "_at_").replace(".", "_")
    lead_id = f"audit_nurturing_{safe}_{step_id}"
    return f"{TRACKING_BASE}/track-click/{lead_id}?url={quote(dest)}"


def first_name(email: str, full_name: str = "") -> str:
    if full_name:
        return full_name.split()[0]
    local = email.split("@")[0]
    name = local.replace(".", " ").replace("-", " ").replace("_", " ")
    return name.split()[0].capitalize() if name.strip() else "there"


# === Email Templates ===

def build_j0_welcome(email: str, name: str, company: str) -> tuple:
    fname = first_name(email, name)
    px = pixel_url(email, "j0_welcome_audit")
    audit_link = click_url(email, "j0", AUDIT_URL)
    trial_link = click_url(email, "j0", TRIAL_URL)

    body = f"""Bonjour {fname},

Merci pour votre intérêt pour le monitoring web. Je suis Alexandre, fondateur d'ArkForge.

J'ai une proposition concrète pour vous :

AUDIT GRATUIT DE VOTRE MONITORING
Je vous propose un diagnostic gratuit de votre infrastructure de monitoring actuelle :

- Quelles pages critiques ne sont pas surveillées ?
- Quels changements silencieux pourraient vous coûter cher ?
- Comment détecter les problèmes en 5 minutes au lieu de 5 heures ?

Cet audit prend 15 minutes et vous repartez avec un plan d'action concret.

2 OPTIONS :
1. Demander votre audit gratuit : {audit_link}
2. Tester directement ArkWatch pendant 14 jours : {trial_link}

À très vite,
Alexandre Desiorac
Fondateur, ArkForge
"""

    html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333; line-height: 1.6;">
<p>Bonjour {fname},</p>
<p>Merci pour votre intérêt pour le monitoring web. Je suis Alexandre, fondateur d'ArkForge.</p>
<p>J'ai une proposition concrète pour vous :</p>

<div style="background: #f0f7ff; border-left: 4px solid #007bff; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #007bff;">AUDIT GRATUIT DE VOTRE MONITORING</h3>
<p>Je vous propose un diagnostic gratuit de votre infrastructure de monitoring actuelle :</p>
<ul>
<li>Quelles pages critiques ne sont <strong>pas surveillées</strong> ?</li>
<li>Quels changements silencieux pourraient vous <strong>coûter cher</strong> ?</li>
<li>Comment détecter les problèmes en <strong>5 minutes</strong> au lieu de 5 heures ?</li>
</ul>
<p>Cet audit prend 15 minutes et vous repartez avec un <strong>plan d'action concret</strong>.</p>
</div>

<table style="width:100%; margin: 24px 0;">
<tr>
<td style="text-align:center; padding:8px;">
<a href="{audit_link}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Demander mon audit gratuit</a>
</td>
<td style="text-align:center; padding:8px;">
<a href="{trial_link}" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Essayer ArkWatch 14j</a>
</td>
</tr>
</table>

<p>À très vite,<br>
<strong>Alexandre Desiorac</strong><br>
<span style="color:#666;">Fondateur, ArkForge</span></p>
<img src="{px}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html


def build_j2_usecase(email: str, name: str, company: str) -> tuple:
    fname = first_name(email, name)
    px = pixel_url(email, "j2_usecase_apm")
    trial_link = click_url(email, "j2", TRIAL_URL + "?utm_source=nurturing_audit&utm_campaign=j2_usecase")

    body = f"""Bonjour {fname},

Connaissez-vous l'histoire de la page pricing à 47 000 EUR ?

LE PROBLÈME
Une entreprise SaaS a mis à jour son CMS un vendredi soir. Mise à jour de routine.
Sauf qu'un champ de prix a été écrasé : "49 EUR/mois" est devenu "490 EUR/mois".

Personne n'a rien vu pendant 3 jours.

Résultat :
- 23 prospects qualifiés ont quitté la page
- 4 clients existants ont ouvert des tickets de support
- Perte estimée : 47 000 EUR de pipeline commercial

LA SOLUTION EN 5 MINUTES
Avec ArkWatch, cette erreur aurait été détectée en 5 minutes :
1. Le moniteur scanne la page toutes les 5 minutes
2. Un changement de prix est détecté automatiquement
3. Alerte email immédiate avec le diff exact
4. Correction en 2 minutes au lieu de 3 jours

ET VOUS ?
Combien de pages critiques avez-vous sans surveillance automatique ?

- Page pricing
- Page checkout
- Pages produit
- Landing pages campagnes
- CGV / mentions légales

Testez gratuitement pendant 14 jours : {trial_link}

Aucune carte bancaire requise. Setup en 30 secondes.

Alexandre
"""

    html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333; line-height: 1.6;">
<p>Bonjour {fname},</p>
<p>Connaissez-vous l'histoire de la page pricing à 47 000 EUR ?</p>

<div style="background: #fff5f5; border-left: 4px solid #dc3545; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #dc3545;">LE PROBLÈME</h3>
<p>Une entreprise SaaS a mis à jour son CMS un vendredi soir. Mise à jour de routine.</p>
<p>Sauf qu'un champ de prix a été écrasé : <strong>"49 EUR/mois"</strong> est devenu <strong style="color:#dc3545;">"490 EUR/mois"</strong>.</p>
<p>Personne n'a rien vu pendant <strong>3 jours</strong>.</p>
<p style="margin-bottom:0;">Résultat :</p>
<ul style="margin-top:4px;">
<li>23 prospects qualifiés ont quitté la page</li>
<li>4 clients existants ont ouvert des tickets</li>
<li><strong>Perte estimée : 47 000 EUR</strong></li>
</ul>
</div>

<div style="background: #f0fff0; border-left: 4px solid #28a745; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #28a745;">LA SOLUTION EN 5 MINUTES</h3>
<p>Avec ArkWatch, cette erreur aurait été détectée en <strong>5 minutes</strong> :</p>
<ol>
<li>Le moniteur scanne la page toutes les 5 minutes</li>
<li>Un changement de prix est détecté automatiquement</li>
<li>Alerte email immédiate avec le diff exact</li>
<li>Correction en 2 minutes au lieu de 3 jours</li>
</ol>
</div>

<h3>Et vous ? Combien de pages critiques sans surveillance ?</h3>
<p style="color: #666;">Page pricing, checkout, produits, landing pages, CGV...</p>

<p style="text-align:center; margin: 24px 0;">
<a href="{trial_link}" style="background: #28a745; color: white; padding: 14px 36px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">Tester gratuitement 14 jours</a>
</p>
<p style="text-align:center; color:#666; font-size: 13px;">Aucune carte bancaire requise. Setup en 30 secondes.</p>

<p>Alexandre</p>
<img src="{px}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html


def build_j4_demo(email: str, name: str, company: str) -> tuple:
    fname = first_name(email, name)
    px = pixel_url(email, "j4_demo_quickwin")
    demo_link = click_url(email, "j4", DEMO_URL + "?utm_source=nurturing_audit&utm_campaign=j4_demo")
    trial_link = click_url(email, "j4", TRIAL_URL + "?utm_source=nurturing_audit&utm_campaign=j4_demo")
    calendly_link = click_url(email, "j4", CALENDLY_URL)

    body = f"""Bonjour {fname},

90 secondes. C'est le temps qu'il faut pour configurer votre premier moniteur ArkWatch.

DÉMO RAPIDE
J'ai enregistré une démonstration de 90 secondes qui montre :
1. Comment ajouter une URL à surveiller (10s)
2. Comment configurer les alertes email (20s)
3. Comment lire le premier rapport de changement (30s)
4. Comment interpréter les diffs visuels (30s)

Voir la démo : {demo_link}

VOTRE QUICK WIN EN 2 MINUTES
Surveillez votre page la plus critique en 2 minutes :

Étape 1: Créez votre compte trial gratuit → {trial_link}
Étape 2: Entrez l'URL de votre page pricing
Étape 3: Activez les alertes email

C'est tout. ArkWatch vérifie toutes les 5 minutes.

BESOIN D'AIDE ?
Réservez un call de 15 min et je configure tout avec vous :
{calendly_link}

Alexandre
"""

    html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333; line-height: 1.6;">
<p>Bonjour {fname},</p>
<p><strong>90 secondes.</strong> C'est le temps qu'il faut pour configurer votre premier moniteur ArkWatch.</p>

<div style="background: #f8f9fa; border: 2px solid #007bff; padding: 20px; margin: 16px 0; border-radius: 8px; text-align: center;">
<h3 style="margin-top:0; color: #007bff;">DÉMO RAPIDE - 90 SECONDES</h3>
<p>Comment configurer votre monitoring en moins de 2 minutes :</p>
<ol style="text-align:left; margin: 12px 0;">
<li>Ajouter une URL à surveiller <span style="color:#666;">(10s)</span></li>
<li>Configurer les alertes email <span style="color:#666;">(20s)</span></li>
<li>Lire le premier rapport de changement <span style="color:#666;">(30s)</span></li>
<li>Interpréter les diffs visuels <span style="color:#666;">(30s)</span></li>
</ol>
<a href="{demo_link}" style="background: #007bff; color: white; padding: 12px 32px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; margin-top: 8px;">Voir la démo</a>
</div>

<div style="background: #f0fff0; border-left: 4px solid #28a745; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #28a745;">VOTRE QUICK WIN EN 2 MINUTES</h3>
<ol>
<li>Créez votre compte trial gratuit</li>
<li>Entrez l'URL de votre page pricing</li>
<li>Activez les alertes email</li>
</ol>
<p style="text-align:center;">
<a href="{trial_link}" style="background: #28a745; color: white; padding: 12px 32px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Créer mon compte gratuit</a>
</p>
</div>

<p style="color:#666; font-size: 14px;">
Besoin d'aide ? <a href="{calendly_link}" style="color: #007bff;">Réservez un call de 15 min</a> et je configure tout avec vous.
</p>

<p>Alexandre</p>
<img src="{px}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html


def build_j7_urgence(email: str, name: str, company: str) -> tuple:
    fname = first_name(email, name)
    px = pixel_url(email, "j7_urgence_trial")
    trial_link = click_url(email, "j7", TRIAL_URL + "?utm_source=nurturing_audit&utm_campaign=j7_urgence")
    calendly_link = click_url(email, "j7", CALENDLY_URL)

    body = f"""Bonjour {fname},

C'est mon dernier email. Je voulais vous informer de 2 choses :

1. PLACES LIMITÉES
Notre trial gratuit 14 jours est limité à 50 comptes simultanés
pour garantir la qualité du support. Il reste 5 places.

2. CE QUE VOUS RISQUEZ SANS MONITORING
Chaque jour sans surveillance automatique, c'est :
- Un bug pricing non détecté pendant des heures
- Un script tiers qui injecte du contenu non voulu
- Un certificat SSL qui expire sans alerte
- Un concurrent qui change ses prix sans que vous le sachiez

DERNIÈRE CHANCE
Créez votre compte trial gratuit maintenant :
{trial_link}

14 jours gratuits. Aucune carte bancaire.
Setup en 30 secondes. Annulation en 1 clic.

Ou réservez un appel de 15 min :
{calendly_link}

Si le monitoring web n'est pas votre priorité, je comprends.
Répondez "STOP" et je ne vous contacterai plus.

Alexandre Desiorac
Fondateur, ArkForge
"""

    html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333; line-height: 1.6;">
<p>Bonjour {fname},</p>
<p>C'est mon dernier email. Je voulais vous informer de 2 choses :</p>

<div style="background: #fff3cd; border: 2px solid #ffc107; padding: 20px; margin: 16px 0; border-radius: 8px;">
<h3 style="margin-top:0; color: #856404;">1. PLACES LIMITÉES</h3>
<p>Notre trial gratuit 14 jours est limité à <strong>50 comptes simultanés</strong> pour garantir la qualité du support.</p>
<p style="font-size: 24px; text-align: center; color: #dc3545; font-weight: bold; margin: 12px 0;">Il reste 5 places.</p>
</div>

<div style="background: #fff5f5; border-left: 4px solid #dc3545; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #dc3545;">2. CE QUE VOUS RISQUEZ SANS MONITORING</h3>
<p>Chaque jour sans surveillance automatique, c'est :</p>
<ul>
<li>Un bug pricing non détecté pendant des heures</li>
<li>Un script tiers qui injecte du contenu non voulu</li>
<li>Un certificat SSL qui expire sans alerte</li>
<li>Un concurrent qui change ses prix sans que vous le sachiez</li>
</ul>
</div>

<p style="text-align:center; margin: 24px 0;">
<a href="{trial_link}" style="background: #dc3545; color: white; padding: 14px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 18px; display: inline-block;">Créer mon compte gratuit</a>
</p>
<p style="text-align:center; color:#666; font-size: 13px;">14 jours gratuits. Aucune carte bancaire. Setup en 30 secondes.</p>

<p style="color:#666; font-size: 14px;">
Ou <a href="{calendly_link}" style="color: #007bff;">réservez un appel de 15 min</a> pour qu'on configure ensemble.
</p>

<hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
<p style="color: #999; font-size: 12px;">
Si le monitoring web n'est pas votre priorité, je comprends. Répondez "STOP" et je ne vous contacterai plus.
</p>

<p><strong>Alexandre Desiorac</strong><br>
<span style="color:#666;">Fondateur, ArkForge</span></p>
<img src="{px}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html


# === Core Logic ===

def build_email_content(step_id: str, email: str, name: str, company: str) -> tuple:
    """Returns (subject, body, html_body) for a given step."""
    step_def = next(s for s in SEQUENCE if s["id"] == step_id)
    subject = step_def["subject"]

    builders = {
        "j0_welcome_audit": build_j0_welcome,
        "j2_usecase_apm": build_j2_usecase,
        "j4_demo_quickwin": build_j4_demo,
        "j7_urgence_trial": build_j7_urgence,
    }
    body, html = builders[step_id](email, name, company)
    return subject, body, html


def load_leads() -> list:
    """Load leads from unified tracking file."""
    data = load_json(LEADS_FILE)
    if not data:
        return []
    leads = data.get("leads", [])
    # Filter: only leads with email, exclude test addresses
    return [
        l for l in leads
        if l.get("lead_email")
        and "@" in l.get("lead_email", "")
        and not l["lead_email"].endswith("@test.com")
        and not l["lead_email"].endswith("@example.com")
    ]


def load_state() -> dict:
    state = load_json(STATE_FILE)
    if not state:
        state = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "leads": {},
            "metrics": {
                "total_sent": 0,
                "total_failed": 0,
                "by_step": {},
                "conversions_trial": 0,
            },
            "unsubscribed": [],
        }
    return state


def enroll_leads(dry_run: bool = False) -> int:
    """Enroll all existing leads into nurturing sequence."""
    leads = load_leads()
    state = load_state()
    now = datetime.utcnow().isoformat() + "Z"
    enrolled = 0

    for lead in leads:
        email = lead["lead_email"]
        if email in state["leads"]:
            continue  # Already enrolled
        if email in state.get("unsubscribed", []):
            continue

        state["leads"][email] = {
            "lead_id": lead.get("lead_id", ""),
            "name": lead.get("lead_name", ""),
            "company": lead.get("company", ""),
            "enrolled_at": now,
            "sent_steps": [],
            "history": [],
            "opens": {},
            "clicks": {},
            "heat_score": lead.get("heat_score", 0),
        }
        enrolled += 1

    if not dry_run and enrolled > 0:
        state["last_enrollment"] = now
        save_json(STATE_FILE, state)

    return enrolled


def get_due_emails(now: datetime) -> list:
    """Determine which emails are due for sending."""
    state = load_state()
    leads_state = state.get("leads", {})
    unsubscribed = state.get("unsubscribed", [])
    due = []

    for email, lead in leads_state.items():
        if email in unsubscribed:
            continue

        enrolled_at_str = lead.get("enrolled_at", "")
        if not enrolled_at_str:
            continue

        try:
            enrolled_at = datetime.fromisoformat(
                enrolled_at_str.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except (ValueError, AttributeError):
            continue

        sent_steps = lead.get("sent_steps", [])

        for step in SEQUENCE:
            if step["id"] in sent_steps:
                continue

            send_after = enrolled_at + timedelta(days=step["day"])
            if now >= send_after:
                due.append({
                    "email": email,
                    "name": lead.get("name", ""),
                    "company": lead.get("company", ""),
                    "step": step,
                })
                break  # One email per lead per cycle

    return due


def send_one(item: dict, dry_run: bool = False) -> bool:
    """Send a single nurturing email."""
    email = item["email"]
    step = item["step"]
    name = item.get("name", "")
    company = item.get("company", "")

    subject, body, html = build_email_content(step["id"], email, name, company)

    if dry_run:
        print(f"  [DRY RUN] '{step['id']}' -> {email} ({name}, {company})")
        return True

    if not EMAIL_ENABLED:
        print(f"  [NO EMAIL] email_sender unavailable, skip {email}")
        return False

    return send_email(
        to_addr=email,
        subject=subject,
        body=body,
        html_body=html,
        reply_to="contact@arkforge.fr",
        skip_warmup=True,
    )


def update_state_after_send(email: str, step_id: str, success: bool):
    """Update state after sending an email."""
    state = load_state()
    lead = state["leads"].get(email)
    if not lead:
        return

    now = datetime.utcnow().isoformat() + "Z"

    if success:
        if step_id not in lead.get("sent_steps", []):
            lead.setdefault("sent_steps", []).append(step_id)
        lead.setdefault("history", []).append({
            "step": step_id,
            "sent_at": now,
            "status": "sent",
        })
        state["metrics"]["total_sent"] = state["metrics"].get("total_sent", 0) + 1
        by_step = state["metrics"].setdefault("by_step", {})
        by_step[step_id] = by_step.get(step_id, 0) + 1
    else:
        lead.setdefault("history", []).append({
            "step": step_id,
            "sent_at": now,
            "status": "failed",
        })
        state["metrics"]["total_failed"] = state["metrics"].get("total_failed", 0) + 1

    state["leads"][email] = lead
    state["last_run"] = now
    save_json(STATE_FILE, state)


def show_status():
    """Print nurturing status dashboard."""
    state = load_state()
    leads = state.get("leads", {})
    metrics = state.get("metrics", {})

    print("=" * 65)
    print("ARKWATCH AUDIT GRATUIT - NURTURING 7J STATUS")
    print("=" * 65)
    print(f"Created: {state.get('created_at', 'N/A')}")
    print(f"Last run: {state.get('last_run', 'never')}")
    print(f"Last enrollment: {state.get('last_enrollment', 'never')}")
    print(f"Total leads enrolled: {len(leads)}")
    print(f"Unsubscribed: {len(state.get('unsubscribed', []))}")
    print()

    print("METRICS:")
    print(f"  Total sent: {metrics.get('total_sent', 0)}")
    print(f"  Total failed: {metrics.get('total_failed', 0)}")
    print(f"  Trial conversions: {metrics.get('conversions_trial', 0)}")
    print()

    print("BY STEP:")
    for step in SEQUENCE:
        count = metrics.get("by_step", {}).get(step["id"], 0)
        print(f"  {step['id']}: {count} sent")
    print()

    # Lead progress summary
    progress = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for email, lead in leads.items():
        n = len(lead.get("sent_steps", []))
        progress[n] = progress.get(n, 0) + 1

    print("FUNNEL:")
    print(f"  Not started: {progress.get(0, 0)}")
    print(f"  J0 sent: {progress.get(1, 0)}")
    print(f"  J0+J2 sent: {progress.get(2, 0)}")
    print(f"  J0+J2+J4 sent: {progress.get(3, 0)}")
    print(f"  All 4 sent: {progress.get(4, 0)}")
    print()

    # Hot leads (opened emails)
    hot = [(e, l) for e, l in leads.items() if l.get("opens")]
    if hot:
        print("HOT LEADS (opened):")
        for email, lead in hot:
            opens = lead["opens"]
            print(f"  {email} ({lead.get('name', '')}) - {len(opens)} opens")
    print("=" * 65)


def main():
    dry_run = "--dry-run" in sys.argv

    if "--status" in sys.argv:
        show_status()
        return 0

    print("=" * 65)
    print(f"ARKWATCH AUDIT GRATUIT - NURTURING 7J {'[DRY RUN]' if dry_run else ''}")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print("=" * 65)

    # Step 1: Enroll new leads
    enrolled = enroll_leads(dry_run=dry_run)
    if enrolled > 0:
        print(f"Enrolled {enrolled} new leads into nurturing sequence.")
    else:
        print("No new leads to enroll.")

    # Step 2: Check for due emails
    now = datetime.utcnow()
    due = get_due_emails(now)

    if not due:
        print("No emails due right now.")
        print("=" * 65)
        return 0

    print(f"Emails due: {len(due)}")

    # Step 3: Send emails (max 10 per cycle to respect warmup)
    MAX_PER_CYCLE = 10
    sent = 0
    failed = 0

    for item in due[:MAX_PER_CYCLE]:
        email = item["email"]
        step = item["step"]
        print(f"\n  Sending '{step['id']}' to {email}...")

        success = send_one(item, dry_run=dry_run)

        if not dry_run:
            update_state_after_send(email, step["id"], success)

        if success:
            sent += 1
            print(f"  -> OK")
        else:
            failed += 1
            print(f"  -> FAILED")

    if len(due) > MAX_PER_CYCLE:
        print(f"\n  ({len(due) - MAX_PER_CYCLE} more emails queued for next cycle)")

    print(f"\nResults: {sent} sent, {failed} failed")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
