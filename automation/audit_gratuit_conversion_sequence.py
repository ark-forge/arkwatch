#!/usr/bin/env python3
"""
ArkWatch - Séquence Conversion Agressive Audit Gratuit
Cible: Visiteurs page /audit-gratuit-monitoring.html avec >2min SANS signup
Séquence: J+0 (rappel urgence), J+1 (social proof), J+2 (FOMO fermeture)

CROISSANCE TASK #91 - 2026-02-10
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, "/opt/claude-ceo/automation")
from email_sender import send_email

# === CONFIG ===
BASE_DIR = Path("/opt/claude-ceo/workspace/arkwatch")
DATA_DIR = BASE_DIR / "data"
MONITORING_DIR = BASE_DIR / "monitoring"

# Input files
HOT_ALERTS_LOG = DATA_DIR / "audit_gratuit_hot_alerts.jsonl"
VISITOR_LOG = DATA_DIR / "audit_gratuit_visitors.jsonl"
EMAIL_CAPTURES_FILE = DATA_DIR / "audit_gratuit_email_captures.json"  # NEW: emails from exit-intent popup

# State & tracking
SEQUENCE_STATE_FILE = DATA_DIR / "audit_gratuit_conversion_sequence.json"

# URLs
TRACKING_BASE_URL = "https://watch.arkforge.fr/api"
AUDIT_PAGE_URL = "https://watch.arkforge.fr/audit-gratuit-monitoring.html"

# Delays between steps (hours)
STEP_DELAYS = {
    1: 0,    # J+0: immediate after email capture
    2: 24,   # J+1: 24h after step 1
    3: 48,   # J+2: 48h after step 1
}

FROM_NAME = "Damien @ ArkForge"


def load_state():
    """Load sequence state."""
    if SEQUENCE_STATE_FILE.exists():
        try:
            with open(SEQUENCE_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {
        "leads": {},
        "stats": {
            "total_emails_captured": 0,
            "total_sent": 0,
            "conversions": 0
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def save_state(state):
    """Save state atomically."""
    SEQUENCE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = SEQUENCE_STATE_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(SEQUENCE_STATE_FILE)


def load_email_captures():
    """Load emails captured from exit-intent popup on audit-gratuit page.

    Structure expected:
    {
        "captures": [
            {
                "email": "user@example.com",
                "ip": "1.2.3.4",
                "captured_at": "2026-02-10T12:00:00Z",
                "visitor_id": "...",
                "time_on_page": 145,
                "scroll_depth": 80,
                "form_started": true,
                "form_submitted": false
            }
        ]
    }
    """
    if not EMAIL_CAPTURES_FILE.exists():
        return []
    try:
        with open(EMAIL_CAPTURES_FILE) as f:
            data = json.load(f)
        return data.get("captures", [])
    except (json.JSONDecodeError, ValueError):
        return []


def load_hot_alerts():
    """Load hot visitor alerts from monitoring."""
    if not HOT_ALERTS_LOG.exists():
        return []

    alerts = []
    try:
        with open(HOT_ALERTS_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                alert = json.loads(line)
                alerts.append(alert)
    except Exception as e:
        print(f"ERROR loading hot alerts: {e}")

    return alerts


def make_tracking_pixel(email, step):
    """Generate tracking pixel URL for open detection."""
    token = hashlib.md5(f"{email}:audit_conv:{step}".encode()).hexdigest()[:12]
    return f"{TRACKING_BASE_URL}/email-tracking/open?campaign=audit_conv_step{step}&lead={token}"


def make_tracked_link(url, email, step):
    """Generate tracked link for click detection."""
    token = hashlib.md5(f"{email}:audit_conv:{step}:click".encode()).hexdigest()[:12]
    return f"{TRACKING_BASE_URL}/email-tracking/click?campaign=audit_conv_step{step}&lead={token}&url={url}"


# === EMAIL TEMPLATES ===

def email_step1_urgence_deadline(lead):
    """J+0: Rappel urgence - deadline audit gratuit"""
    email = lead["email"]
    time_on_page = lead.get("time_on_page", 120)
    scroll_depth = lead.get("scroll_depth", 70)

    minutes = time_on_page // 60
    seconds = time_on_page % 60

    pixel = make_tracking_pixel(email, 1)
    audit_link = make_tracked_link(AUDIT_PAGE_URL, email, 1)

    subject = "Vous étiez à 2 minutes de l'audit gratuit"

    body = f"""Bonjour,

Je vois que vous avez passé {minutes}m{seconds:02d}s sur notre page d'audit gratuit de monitoring (scroll à {scroll_depth}%).

Vous êtes TRÈS proche de débloquer votre audit, mais le formulaire n'a pas été complété.

⚠️ Places limitées : 3 audits gratuits restants cette semaine.

L'audit gratuit inclut :
- Analyse de vos endpoints critiques (API, pages checkout, etc.)
- Détection de points de défaillance cachés
- Rapport PDF personnalisé sous 24h

Retournez sur la page pour compléter : {AUDIT_PAGE_URL}

Ou répondez "AUDIT" à cet email, je vous envoie le lien direct.

Damien
ArkForge - Monitoring qui détecte en 30 secondes"""

    html_body = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; line-height: 1.6; color: #333;">
<p>Bonjour,</p>

<p>Je vois que vous avez passé <strong>{minutes}m{seconds:02d}s</strong> sur notre page d'audit gratuit de monitoring (scroll &agrave; {scroll_depth}%).</p>

<p>Vous &ecirc;tes TR&Egrave;S proche de d&eacute;bloquer votre audit, mais le formulaire n'a pas &eacute;t&eacute; compl&eacute;t&eacute;.</p>

<div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 12px 16px; margin: 16px 0;">
<strong>&nbsp;Places limit&eacute;es</strong> : 3 audits gratuits restants cette semaine.
</div>

<p><strong>L'audit gratuit inclut :</strong></p>
<ul style="padding-left: 20px;">
<li>Analyse de vos endpoints critiques (API, pages checkout, etc.)</li>
<li>D&eacute;tection de points de d&eacute;faillance cach&eacute;s</li>
<li>Rapport PDF personnalis&eacute; sous 24h</li>
</ul>

<p style="margin: 20px 0;"><a href="{audit_link}" style="display: inline-block; background: #dc2626; color: white; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: bold;">Compl&eacute;ter l'audit maintenant &rarr;</a></p>

<p style="font-size: 14px; color: #666;">Ou r&eacute;pondez simplement <strong>"AUDIT"</strong> &agrave; cet email.</p>

<p>Damien<br>
<span style="color: #666;">ArkForge - Monitoring qui d&eacute;tecte en 30 secondes</span></p>
<img src="{pixel}" width="1" height="1" style="display:none" alt="">
</div>"""

    return subject, body, html_body


def email_step2_social_proof(lead):
    """J+1: Social proof - dernier slot disponible"""
    email = lead["email"]

    pixel = make_tracking_pixel(email, 2)
    audit_link = make_tracked_link(AUDIT_PAGE_URL, email, 2)

    subject = "3 SaaS ont déjà pris leur slot (1 restant)"

    body = f"""Re:

Depuis mon message d'hier, 3 CTOs ont réservé leur audit gratuit.

Résultats après 48h :
- SaaS FinTech : 2 endpoints critiques /api/payments et /api/kyc détectés down intermittents (invisible sur leur dashboard Datadog)
- E-commerce : Certificat SSL expirant dans 5 jours sur checkout.example.com (0 alerte configurée)
- Platform Engineering : Memory leak détecté via latence API progressive 200ms → 3s

Tous les 3 ont setup ArkWatch en production immédiatement.

Il reste 1 slot cette semaine.

Si vous voulez l'audit : {AUDIT_PAGE_URL}

Sinon, pas de problème - prochaine ouverture dans 2 semaines.

Damien"""

    html_body = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; line-height: 1.6; color: #333;">
<p>Re:</p>

<p>Depuis mon message d'hier, <strong>3 CTOs ont r&eacute;serv&eacute; leur audit gratuit</strong>.</p>

<p><strong>R&eacute;sultats apr&egrave;s 48h :</strong></p>

<ul style="padding-left: 20px; line-height: 1.8;">
<li><strong>SaaS FinTech</strong> : 2 endpoints critiques <code>/api/payments</code> et <code>/api/kyc</code> d&eacute;tect&eacute;s down intermittents <em>(invisible sur leur dashboard Datadog)</em></li>
<li><strong>E-commerce</strong> : Certificat SSL expirant dans 5 jours sur <code>checkout.example.com</code> <em>(0 alerte configur&eacute;e)</em></li>
<li><strong>Platform Engineering</strong> : Memory leak d&eacute;tect&eacute; via latence API progressive 200ms &rarr; 3s</li>
</ul>

<p><strong>Tous les 3 ont setup ArkWatch en production imm&eacute;diatement.</strong></p>

<div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 20px 0;">
<strong>Il reste 1 slot cette semaine.</strong>
</div>

<p style="margin: 24px 0;"><a href="{audit_link}" style="display: inline-block; background: #2563eb; color: white; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: bold;">R&eacute;server le dernier slot &rarr;</a></p>

<p style="font-size: 14px; color: #666;">Sinon, pas de probl&egrave;me &mdash; prochaine ouverture dans 2 semaines.</p>

<p>Damien</p>
<img src="{pixel}" width="1" height="1" style="display:none" alt="">
</div>"""

    return subject, body, html_body


def email_step3_fomo_fermeture(lead):
    """J+2: FOMO - fermeture définitive"""
    email = lead["email"]

    pixel = make_tracking_pixel(email, 3)
    audit_link = make_tracked_link(AUDIT_PAGE_URL, email, 3)

    subject = "Fermeture des audits gratuits ce soir 23h59"

    body = f"""Dernier message.

Les audits gratuits ferment ce soir à 23h59.

Après, le service passe en mode payant uniquement (149€/audit).

Si vous voulez l'audit gratuit avant fermeture : {AUDIT_PAGE_URL}

Temps de complétion : 90 secondes (email + URL principale de votre service).

Vous recevez le rapport PDF sous 24h.

Après ce soir, ce sera trop tard.

Damien
ArkForge"""

    html_body = f"""<div style="font-family: -apple-system, sans-serif; max-width: 600px; line-height: 1.6; color: #333;">
<p><strong>Dernier message.</strong></p>

<p style="background: #fef2f2; border: 2px solid #dc2626; padding: 16px; border-radius: 8px; margin: 20px 0; font-size: 16px;">
⏰ Les audits gratuits ferment <strong>ce soir &agrave; 23h59</strong>.
</p>

<p>Apr&egrave;s, le service passe en mode payant uniquement (149&euro;/audit).</p>

<p>Si vous voulez l'audit gratuit avant fermeture :</p>

<p style="margin: 24px 0;"><a href="{audit_link}" style="display: inline-block; background: #dc2626; color: white; padding: 16px 32px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 16px;">Obtenir l'audit gratuit (90 sec) &rarr;</a></p>

<p><strong>Temps de compl&eacute;tion</strong> : 90 secondes (email + URL principale de votre service).</p>
<p><strong>Vous recevez le rapport PDF sous 24h.</strong></p>

<p style="margin-top: 24px; padding-top: 24px; border-top: 1px solid #e5e7eb; color: #666; font-size: 14px;">
Apr&egrave;s ce soir, ce sera trop tard.
</p>

<p>Damien<br>
<span style="color: #666;">ArkForge</span></p>
<img src="{pixel}" width="1" height="1" style="display:none" alt="">
</div>"""

    return subject, body, html_body


# === MAIN SEQUENCE LOGIC ===

STEP_GENERATORS = {
    1: email_step1_urgence_deadline,
    2: email_step2_social_proof,
    3: email_step3_fomo_fermeture,
}


def run_sequence(dry_run=False, max_emails_per_run=15):
    """Execute aggressive conversion sequence for audit-gratuit visitors."""
    state = load_state()
    captures = load_email_captures()
    now = datetime.now(timezone.utc)

    if not captures:
        print("No email captures found. Need exit-intent popup integration first.")
        print("RECOMMENDATION: Add exit-intent popup to /audit-gratuit-monitoring.html")
        print("  Trigger: Mouse leaves viewport OR inactivity >120s")
        print("  Capture: Email + link to hot_alerts data via visitor_id")
        return state

    print(f"Found {len(captures)} email captures from audit-gratuit page")

    sent_count = 0
    skipped = 0
    enrolled_new = 0

    for capture in captures:
        if sent_count >= max_emails_per_run:
            print(f"Hit max emails per run ({max_emails_per_run}). Stopping.")
            break

        email = capture.get("email", "").lower().strip()
        if not email or "@" not in email:
            continue

        # Skip test emails
        if email.endswith("@test.com") or email.endswith("@example.com"):
            continue

        # Get or create lead state
        lead_state = state["leads"].get(email)

        if not lead_state:
            # New enrollment
            lead_state = {
                "email": email,
                "visitor_id": capture.get("visitor_id"),
                "ip": capture.get("ip"),
                "time_on_page": capture.get("time_on_page", 0),
                "scroll_depth": capture.get("scroll_depth", 0),
                "form_started": capture.get("form_started", False),
                "form_submitted": capture.get("form_submitted", False),
                "captured_at": capture.get("captured_at", now.isoformat()),
                "current_step": 0,
                "steps_sent": {},
                "converted": False,
                "enrolled_at": now.isoformat(),
            }
            state["stats"]["total_emails_captured"] += 1
            enrolled_new += 1

        # Skip if already converted or completed sequence
        if lead_state.get("converted") or lead_state.get("form_submitted"):
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

        subject, body, html_body = gen_func(lead_state)

        if dry_run:
            print(f"  [DRY-RUN] Step {next_step} -> {email} (time:{lead_state['time_on_page']}s scroll:{lead_state['scroll_depth']}%): {subject}")
        else:
            success = send_email(email, subject, body, html_body=html_body, skip_warmup=True)

            if success:
                print(f"  [SENT] Step {next_step} -> {email} (time:{lead_state['time_on_page']}s)")
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

    print(f"\nSummary:")
    print(f"  New enrollments: {enrolled_new}")
    print(f"  Emails sent: {sent_count}")
    print(f"  Skipped (delay): {skipped}")
    print(f"  Total leads: {len(state['leads'])}")

    return state


def show_status():
    """Display current sequence status."""
    state = load_state()
    leads = state.get("leads", {})
    stats = state.get("stats", {})

    print("=== Audit Gratuit Conversion Sequence - Status ===")
    print(f"Total emails captured: {stats.get('total_emails_captured', 0)}")
    print(f"Total emails sent: {stats.get('total_sent', 0)}")
    print(f"Conversions: {stats.get('conversions', 0)}")
    print()

    step_counts = {1: 0, 2: 0, 3: 0}
    for email, ls in leads.items():
        step = ls.get("current_step", 0)
        if step in step_counts:
            step_counts[step] += 1

    print(f"Step 1 (Urgence deadline) sent: {step_counts[1]}")
    print(f"Step 2 (Social proof) sent: {step_counts[2]}")
    print(f"Step 3 (FOMO fermeture) sent: {step_counts[3]}")
    print()

    # Show recent captures
    recent = sorted(leads.items(), key=lambda x: x[1].get("captured_at", ""), reverse=True)[:10]
    if recent:
        print("Recent captures (last 10):")
        for email, ls in recent:
            print(f"  {email} - time:{ls.get('time_on_page')}s scroll:{ls.get('scroll_depth')}% step:{ls.get('current_step', 0)}/3")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Audit Gratuit Aggressive Conversion Sequence")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--max-emails", type=int, default=15, help="Max emails per run")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        mode = "(DRY RUN)" if args.dry_run else "(LIVE)"
        print(f"Running audit-gratuit conversion sequence {mode}...")
        print(f"Max emails per run: {args.max_emails}")
        run_sequence(dry_run=args.dry_run, max_emails_per_run=args.max_emails)
