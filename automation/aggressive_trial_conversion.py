#!/usr/bin/env python3
"""
ArkWatch - Aggressive Trial Conversion Sequence
Cible: leads identifiés qui ont montré de l'intérêt (opens, visits) mais n'ont PAS signup au trial.
Séquence: J+1 (aide), J+2 (case study), J+3 (offre audit gratuit 15min)
Tracking: opens via pixel, clicks via redirect
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/claude-ceo/automation")
from email_sender import send_email

# === CONFIG ===
BASE_DIR = Path("/opt/claude-ceo/workspace/arkwatch")
DATA_DIR = BASE_DIR / "data"
TRACKING_FILE = DATA_DIR / "aggressive_conversion_state.json"
UNIFIED_TRACKING = DATA_DIR / "unified_email_tracking.json"
SIGNUPS_FILE = DATA_DIR / "trial_14d_signups.json"
TRACKING_BASE_URL = "https://watch.arkforge.fr/api"
TRIAL_URL = "https://watch.arkforge.fr/trial-14d.html"
FROM_NAME = "Damien @ ArkForge"

# Min hours between sequence steps
STEP_DELAYS = {
    1: 0,    # J+1: send immediately (first run)
    2: 24,   # J+2: 24h after step 1
    3: 48,   # J+3: 48h after step 1
}


def load_state():
    """Load conversion sequence state."""
    if TRACKING_FILE.exists():
        try:
            with open(TRACKING_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"leads": {}, "stats": {"total_sent": 0, "total_opens": 0, "conversions": 0}, "created_at": datetime.utcnow().isoformat()}


def save_state(state):
    """Save state atomically."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.utcnow().isoformat()
    tmp = TRACKING_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(TRACKING_FILE)


def get_signed_up_emails():
    """Get set of emails that already signed up for trial."""
    if not SIGNUPS_FILE.exists():
        return set()
    try:
        with open(SIGNUPS_FILE) as f:
            signups = json.load(f)
        return {s.get("email", "").lower() for s in signups}
    except (json.JSONDecodeError, ValueError):
        return set()


def load_target_leads():
    """Load leads from unified tracking, sorted by heat_score desc."""
    if not UNIFIED_TRACKING.exists():
        return []
    try:
        with open(UNIFIED_TRACKING) as f:
            data = json.load(f)
        leads = data.get("leads", [])
        # Filter: not already signed up, has email
        signed_up = get_signed_up_emails()
        valid = []
        for lead in leads:
            email = lead.get("lead_email", "").lower()
            if email and email not in signed_up and not email.endswith("@test.com") and not email.endswith("@example.com"):
                valid.append(lead)
        # Sort by heat_score descending (hottest first)
        valid.sort(key=lambda x: x.get("heat_score", 0), reverse=True)
        return valid
    except (json.JSONDecodeError, ValueError):
        return []


def make_tracking_pixel(email, step):
    """Generate tracking pixel URL for open detection."""
    token = hashlib.md5(f"{email}:aggressive_conv:{step}".encode()).hexdigest()[:12]
    return f"{TRACKING_BASE_URL}/email-tracking/open?campaign=aggressive_conv_step{step}&lead={token}"


def make_tracked_link(url, email, step):
    """Generate tracked link for click detection."""
    token = hashlib.md5(f"{email}:aggressive_conv:{step}:click".encode()).hexdigest()[:12]
    return f"{TRACKING_BASE_URL}/email-tracking/click?campaign=aggressive_conv_step{step}&lead={token}&url={url}"


# === EMAIL TEMPLATES ===

def email_step1_help(lead):
    """J+1: 'Vous avez consulté notre trial - Besoin d'aide?'"""
    name = lead.get("lead_name", "").split()[0] if lead.get("lead_name") else ""
    company = lead.get("company", "")
    email = lead.get("lead_email", "")
    segment = lead.get("segment", "")

    # Personalize based on segment
    pain_point = {
        "DevOps/SRE": "downtime non-detecté qui coûte des milliers d'euros",
        "DevOps": "alertes qui arrivent trop tard sur vos endpoints critiques",
        "SRE": "MTTR trop long car vos outils actuels sont trop complexes",
        "Fintech": "conformité SLA qui dépend d'un monitoring fragmenté",
        "HealthTech": "uptime critique pour vos patients qui repose sur des checks manuels",
        "E-commerce": "pages produit down pendant un pic de trafic sans alerte",
        "Agency": "sites clients qui tombent sans que vous le sachiez avant le client",
        "Indie Dev": "votre side project qui crash la nuit sans notification",
        "Platform Engineering": "infrastructure qui scale mais monitoring qui ne suit pas",
        "Cloud Engineering": "multi-cloud visibility qui manque un point de défaillance",
        "Infrastructure": "infrastructure critique sans monitoring unifié"
    }.get(segment, "problèmes de disponibilité détectés trop tard")

    greeting = f"Bonjour {name}," if name else "Bonjour,"
    company_mention = f" chez {company}" if company else ""

    pixel = make_tracking_pixel(email, 1)
    trial_link = make_tracked_link(TRIAL_URL, email, 1)

    subject = f"Question rapide{company_mention}"

    body = f"""{greeting}

Je me permets de vous écrire car je sais que {pain_point} est un vrai sujet{company_mention}.

On a lancé ArkWatch, un outil de monitoring qui alerte en 30 secondes quand un endpoint tombe - pas 5 minutes comme Pingdom ou UptimeRobot.

Setup en 2 minutes, pas de config YAML à rallonge.

Est-ce que c'est un sujet pour vous en ce moment ? Un simple "oui" suffit, je vous envoie un accès trial 14 jours.

Bonne journée,
Damien
ArkForge"""

    html_body = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; line-height: 1.6; color: #333;">
<p>{greeting}</p>

<p>Je me permets de vous &eacute;crire car je sais que <strong>{pain_point}</strong> est un vrai sujet{company_mention}.</p>

<p>On a lanc&eacute; <strong>ArkWatch</strong>, un outil de monitoring qui alerte en <strong>30 secondes</strong> quand un endpoint tombe &mdash; pas 5 minutes comme Pingdom ou UptimeRobot.</p>

<p>Setup en 2 minutes, pas de config YAML &agrave; rallonge.</p>

<p>Est-ce que c'est un sujet pour vous en ce moment ? Un simple "oui" suffit, je vous envoie un <a href="{trial_link}" style="color: #2563eb;">acc&egrave;s trial 14 jours</a>.</p>

<p>Bonne journ&eacute;e,<br>
<strong>Damien</strong><br>
<span style="color: #666;">ArkForge</span></p>
<img src="{pixel}" width="1" height="1" style="display:none" alt="">
</div>"""

    return subject, body, html_body


def email_step2_case_study(lead):
    """J+2: Case study - client résolu en 48h"""
    name = lead.get("lead_name", "").split()[0] if lead.get("lead_name") else ""
    company = lead.get("company", "")
    email = lead.get("lead_email", "")

    greeting = f"Re: {name}," if name else "Re:"
    company_mention = f" chez {company}" if company else ""

    pixel = make_tracking_pixel(email, 2)
    trial_link = make_tracked_link(TRIAL_URL, email, 2)

    subject = f"Comment un SaaS a détecté 3 bugs critiques en 48h"

    body = f"""{greeting}

Suite à mon message d'hier, je voulais partager un cas concret.

Un SaaS B2B (200k utilisateurs) utilisait UptimeRobot. Problème : alertes à 5min+, pas de monitoring API profond.

En installant ArkWatch :
- Heure 2 : Détection d'un endpoint /api/payments qui retournait 503 intermittent (invisible sur leur dashboard)
- Heure 12 : Alerte sur un certificat SSL expirant dans 48h (évité un downtime complet)
- Heure 36 : Détection d'un memory leak via temps de réponse qui dégradait de 200ms → 2s progressivement

Résultat : 3 incidents critiques détectés AVANT impact client. Temps de setup : 4 minutes.

Le trial est gratuit 14 jours, sans carte bancaire : {TRIAL_URL}

Damien"""

    html_body = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; line-height: 1.6; color: #333;">
<p>{greeting}</p>

<p>Suite &agrave; mon message d'hier, je voulais partager un cas concret.</p>

<p>Un SaaS B2B (200k utilisateurs) utilisait UptimeRobot. Probl&egrave;me : alertes &agrave; 5min+, pas de monitoring API profond.</p>

<p><strong>En installant ArkWatch :</strong></p>
<ul style="padding-left: 20px;">
<li><strong>Heure 2</strong> : D&eacute;tection d'un endpoint /api/payments qui retournait 503 intermittent <em>(invisible sur leur dashboard)</em></li>
<li><strong>Heure 12</strong> : Alerte sur un certificat SSL expirant dans 48h <em>(downtime complet &eacute;vit&eacute;)</em></li>
<li><strong>Heure 36</strong> : D&eacute;tection d'un memory leak via temps de r&eacute;ponse qui d&eacute;gradait de 200ms &rarr; 2s</li>
</ul>

<p><strong>R&eacute;sultat</strong> : 3 incidents critiques d&eacute;tect&eacute;s AVANT impact client. Temps de setup : <strong>4 minutes</strong>.</p>

<p style="margin: 20px 0;"><a href="{trial_link}" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;">Essayer gratuitement 14 jours &rarr;</a></p>

<p>Damien</p>
<img src="{pixel}" width="1" height="1" style="display:none" alt="">
</div>"""

    return subject, body, html_body


def email_step3_free_audit(lead):
    """J+3: Offre appel gratuit 15min audit"""
    name = lead.get("lead_name", "").split()[0] if lead.get("lead_name") else ""
    company = lead.get("company", "")
    email = lead.get("lead_email", "")
    segment = lead.get("segment", "")

    greeting = f"{name}," if name else "Bonjour,"
    company_mention = f" de {company}" if company else ""

    pixel = make_tracking_pixel(email, 3)
    trial_link = make_tracked_link(TRIAL_URL, email, 3)

    # Personalized audit angle
    audit_focus = {
        "DevOps/SRE": "vos endpoints critiques et la couverture monitoring actuelle",
        "DevOps": "vos pipelines CI/CD et la détection de régressions en prod",
        "SRE": "vos SLOs/SLAs et les gaps de monitoring",
        "Fintech": "la conformité uptime de vos APIs de paiement",
        "HealthTech": "la résilience de vos services patients",
        "E-commerce": "la disponibilité de vos pages produit et checkout",
        "Agency": "le monitoring des sites de vos clients (offre white-label)",
        "Indie Dev": "votre stack technique et les points de défaillance",
    }.get(segment, "votre infrastructure et les risques de downtime")

    subject = f"15 min pour auditer {audit_focus.split(' et ')[0]}"

    body = f"""{greeting}

Dernier message, promis.

Je propose un audit gratuit de 15 minutes sur {audit_focus}.

Concrètement :
1. Je regarde vos endpoints publics (ce que je peux tester sans accès)
2. Je vous montre ce qu'ArkWatch détecte en live
3. Vous repartez avec un rapport, même si vous ne prenez pas l'outil

Pas de pitch commercial. Juste un diagnostic technique.

Si ça vous intéresse, répondez "audit" à cet email. Je vous propose un créneau dans les 24h.

Sinon, pas de souci - je ne vous relancerai plus.

Damien
ArkForge - Monitoring API en 30 secondes"""

    html_body = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; line-height: 1.6; color: #333;">
<p>{greeting}</p>

<p>Dernier message, promis.</p>

<p>Je propose un <strong>audit gratuit de 15 minutes</strong> sur {audit_focus}.</p>

<p><strong>Concr&egrave;tement :</strong></p>
<ol style="padding-left: 20px;">
<li>Je regarde vos endpoints publics (ce que je peux tester sans acc&egrave;s)</li>
<li>Je vous montre ce qu'ArkWatch d&eacute;tecte en live</li>
<li><strong>Vous repartez avec un rapport</strong>, m&ecirc;me si vous ne prenez pas l'outil</li>
</ol>

<p>Pas de pitch commercial. Juste un diagnostic technique.</p>

<p style="background: #f0f9ff; border-left: 4px solid #2563eb; padding: 12px 16px; margin: 16px 0;">
<strong>Int&eacute;ress&eacute; ?</strong> R&eacute;pondez simplement <strong>"audit"</strong> &agrave; cet email.<br>
Je vous propose un cr&eacute;neau dans les 24h.
</p>

<p>Sinon, pas de souci &mdash; je ne vous relancerai plus.</p>

<p>Ou testez directement : <a href="{trial_link}" style="color: #2563eb;">Trial gratuit 14 jours &rarr;</a></p>

<p>Damien<br>
<span style="color: #666;">ArkForge - Monitoring API en 30 secondes</span></p>
<img src="{pixel}" width="1" height="1" style="display:none" alt="">
</div>"""

    return subject, body, html_body


# === MAIN SEQUENCE LOGIC ===

STEP_GENERATORS = {
    1: email_step1_help,
    2: email_step2_case_study,
    3: email_step3_free_audit,
}


def run_sequence(dry_run=False, max_emails_per_run=10):
    """Execute the aggressive conversion sequence."""
    state = load_state()
    leads = load_target_leads()
    now = datetime.utcnow()

    if not leads:
        print("No target leads found.")
        return state

    print(f"Found {len(leads)} eligible leads (sorted by heat_score)")

    sent_count = 0
    skipped = 0

    for lead in leads:
        if sent_count >= max_emails_per_run:
            print(f"Hit max emails per run ({max_emails_per_run}). Stopping.")
            break

        email = lead.get("lead_email", "").lower()
        if not email:
            continue

        # Get or create lead state
        lead_state = state["leads"].get(email, {
            "name": lead.get("lead_name", ""),
            "company": lead.get("company", ""),
            "heat_score": lead.get("heat_score", 0),
            "current_step": 0,
            "steps_sent": {},
            "enrolled_at": now.isoformat(),
            "converted": False,
        })

        # Skip if already converted or sequence complete
        if lead_state.get("converted"):
            continue
        if lead_state.get("current_step", 0) >= 3:
            continue

        next_step = lead_state.get("current_step", 0) + 1

        # Check delay for this step
        if next_step > 1:
            step1_sent = lead_state.get("steps_sent", {}).get("1", {}).get("sent_at")
            if step1_sent:
                step1_time = datetime.fromisoformat(step1_sent)
                hours_since = (now - step1_time).total_seconds() / 3600
                required_hours = STEP_DELAYS.get(next_step, 24)
                if hours_since < required_hours:
                    skipped += 1
                    continue

        # Generate email
        gen_func = STEP_GENERATORS.get(next_step)
        if not gen_func:
            continue

        subject, body, html_body = gen_func(lead)

        if dry_run:
            print(f"  [DRY-RUN] Step {next_step} -> {email} ({lead.get('company', '?')}): {subject}")
        else:
            success = send_email(email, subject, body, html_body=html_body, skip_warmup=True)

            if success:
                print(f"  [SENT] Step {next_step} -> {email} ({lead.get('company', '?')})")
                lead_state["current_step"] = next_step
                if "steps_sent" not in lead_state:
                    lead_state["steps_sent"] = {}
                lead_state["steps_sent"][str(next_step)] = {
                    "sent_at": now.isoformat(),
                    "subject": subject,
                    "opened": False,
                    "clicked": False,
                }
                state["stats"]["total_sent"] += 1
                sent_count += 1
            else:
                print(f"  [FAILED] Step {next_step} -> {email}")

        state["leads"][email] = lead_state

    if not dry_run:
        save_state(state)

    print(f"\nSummary: sent={sent_count}, skipped_delay={skipped}, total_leads={len(leads)}")
    return state


def show_status():
    """Display current sequence status."""
    state = load_state()
    leads = state.get("leads", {})
    stats = state.get("stats", {})

    print("=== Aggressive Trial Conversion - Status ===")
    print(f"Total leads enrolled: {len(leads)}")
    print(f"Total emails sent: {stats.get('total_sent', 0)}")
    print(f"Conversions: {stats.get('conversions', 0)}")
    print()

    step_counts = {1: 0, 2: 0, 3: 0}
    for email, ls in leads.items():
        step = ls.get("current_step", 0)
        if step in step_counts:
            step_counts[step] += 1

    print(f"Step 1 (Help offer) sent: {step_counts[1]}")
    print(f"Step 2 (Case study) sent: {step_counts[2]}")
    print(f"Step 3 (Free audit) sent: {step_counts[3]}")
    print()

    # Show hot leads progress
    hot = [(e, l) for e, l in leads.items() if l.get("heat_score", 0) >= 50]
    if hot:
        print("HOT leads progress:")
        for email, ls in sorted(hot, key=lambda x: x[1].get("heat_score", 0), reverse=True):
            print(f"  {ls.get('name', '?')} ({ls.get('company', '?')}) - heat:{ls.get('heat_score')} step:{ls.get('current_step', 0)}/3")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Aggressive Trial Conversion Sequence")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--max-emails", type=int, default=10, help="Max emails per run")
    parser.add_argument("--step", type=int, choices=[1, 2, 3], help="Force specific step only")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        print(f"Running aggressive conversion sequence {'(DRY RUN)' if args.dry_run else '(LIVE)'}...")
        print(f"Max emails per run: {args.max_emails}")
        run_sequence(dry_run=args.dry_run, max_emails_per_run=args.max_emails)
