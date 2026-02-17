#!/usr/bin/env python3
"""Email J+0 Post-Visit Automation for Audit Gratuit leads.

Sends a commercial follow-up email 2 hours after a visitor leaves the audit page
WITHOUT submitting the form or triggering the exit-intent popup.

Data sources:
- audit_gratuit_visitors.jsonl (visitor events from page tracker)
- audit_gratuit_tracking.json (submitted forms - exclusion list)
- audit_gratuit_exit_captures.json (exit-intent captures - exclusion list)
- post_visit_email_state.json (sent tracking to avoid duplicates)

Run via cron every 30 minutes:
  */30 * * * * python3 /opt/claude-ceo/workspace/arkwatch/automation/email_j0_post_visit.py
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
VISITORS_FILE = DATA_DIR / "audit_gratuit_visitors.jsonl"
AUDIT_TRACKING_FILE = DATA_DIR / "audit_gratuit_tracking.json"
EXIT_CAPTURES_FILE = DATA_DIR / "audit_gratuit_exit_captures.json"
STATE_FILE = DATA_DIR / "post_visit_email_state.json"

# Config
MIN_TIME_ON_PAGE = 60  # Minimum 60s on page to qualify
MIN_SCROLL_DEPTH = 30  # Minimum 30% scroll to show interest
DELAY_HOURS = 2        # Wait 2h after last visit activity
MAX_EMAILS_PER_RUN = 5 # Cap to respect warmup limits

BOOKING_URL = "https://calendly.com/arkforge/audit-monitoring-15min"
AUDIT_PAGE_URL = "https://arkforge.fr/audit-gratuit-monitoring.html"
CHECKOUT_STARTER_URL = "https://buy.stripe.com/00w7sE8li8aU2iA8Uo4AU04"
TRIAL_14D_URL = "https://arkforge.fr/trial-14d.html"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.load(open(STATE_FILE))
        except (json.JSONDecodeError, OSError):
            pass
    return {"sent_visitor_ids": [], "last_run": None, "total_sent": 0}


def save_state(state: dict):
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_FILE)


def load_excluded_emails() -> set:
    """Load emails that already converted (form submitted or exit-intent captured)."""
    excluded = set()

    # Emails from audit form submissions
    if AUDIT_TRACKING_FILE.exists():
        try:
            data = json.load(open(AUDIT_TRACKING_FILE))
            for s in data.get("submissions", []):
                excluded.add(s.get("email", "").lower())
        except (json.JSONDecodeError, OSError):
            pass

    # Emails from exit-intent captures (already receiving J+0 relance)
    if EXIT_CAPTURES_FILE.exists():
        try:
            data = json.load(open(EXIT_CAPTURES_FILE))
            for c in data.get("captures", []):
                excluded.add(c.get("email", "").lower())
        except (json.JSONDecodeError, OSError):
            pass

    return excluded


def parse_visitors() -> dict:
    """Parse visitor events from JSONL, aggregate per visitor_id."""
    visitors = defaultdict(lambda: {
        "events": [],
        "max_scroll": 0,
        "total_time": 0,
        "form_started": False,
        "form_submitted": False,
        "email": None,
        "last_activity": None,
        "first_seen": None,
    })

    if not VISITORS_FILE.exists():
        return visitors

    with open(VISITORS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            vid = event.get("visitor_id")
            if not vid:
                continue

            v = visitors[vid]
            v["events"].append(event)

            ts = event.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if v["first_seen"] is None or dt < v["first_seen"]:
                        v["first_seen"] = dt
                    if v["last_activity"] is None or dt > v["last_activity"]:
                        v["last_activity"] = dt
                except (ValueError, TypeError):
                    pass

            etype = event.get("type", "")
            if etype == "scroll":
                depth = event.get("depth", 0)
                if depth > v["max_scroll"]:
                    v["max_scroll"] = depth
            elif etype == "form_focus" or etype == "form_input":
                v["form_started"] = True
            elif etype == "form_submit":
                v["form_submitted"] = True

            top = event.get("time_on_page", 0)
            if top > v["total_time"]:
                v["total_time"] = top

    return visitors


def find_eligible_visitors(visitors: dict, state: dict) -> list:
    """Find visitors eligible for 2h post-visit email."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=DELAY_HOURS)
    already_sent = set(state.get("sent_visitor_ids", []))
    excluded_emails = load_excluded_emails()

    eligible = []
    for vid, v in visitors.items():
        # Skip if already sent
        if vid in already_sent:
            continue
        # Skip if form was submitted (already converted)
        if v["form_submitted"]:
            continue
        # Skip if no last_activity or activity too recent (< 2h)
        if v["last_activity"] is None or v["last_activity"] > cutoff:
            continue
        # Skip if not enough engagement
        if v["total_time"] < MIN_TIME_ON_PAGE:
            continue
        if v["max_scroll"] < MIN_SCROLL_DEPTH:
            continue
        # Skip visitors older than 48h (stale)
        if v["first_seen"] and v["first_seen"] < (now - timedelta(hours=48)):
            continue

        # Check if we have email from any event (form_input with email field)
        email = None
        for event in v["events"]:
            if event.get("type") == "form_input" and event.get("field") == "email":
                email = event.get("value")
                break

        # If no email captured from form input, skip (we can't email them)
        if not email:
            continue

        # Skip if email already converted elsewhere
        if email.lower() in excluded_emails:
            continue

        eligible.append({
            "visitor_id": vid,
            "email": email,
            "time_on_page": v["total_time"],
            "max_scroll": v["max_scroll"],
            "form_started": v["form_started"],
            "last_activity": v["last_activity"].isoformat(),
        })

    # Sort by engagement (time on page * scroll depth) descending
    eligible.sort(key=lambda x: x["time_on_page"] * x["max_scroll"], reverse=True)
    return eligible[:MAX_EMAILS_PER_RUN]


def build_commercial_email(lead: dict) -> tuple:
    """Build the 2h post-visit commercial email (subject, text, html)."""
    time_sec = lead["time_on_page"]
    time_min = time_sec // 60
    time_str = f"{time_min} minute{'s' if time_min > 1 else ''}" if time_min >= 1 else f"{time_sec}s"

    tracking_id = f"post_visit_2h_{lead['visitor_id']}"
    tracking_pixel = (
        f'<img src="https://watch.arkforge.fr/track/open/{tracking_id}" '
        f'width="1" height="1" style="display:none;" alt="" />'
    )

    subject = "Votre monitoring merite mieux — offre speciale 48h"

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;">

<div style="background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 22px;">Votre stack merite un monitoring professionnel</h1>
    <p style="margin: 8px 0 0; opacity: 0.9;">Offre valable 48h</p>
</div>

<div style="background: white; padding: 25px; border-radius: 12px; border: 1px solid #e5e7eb;">
    <p>Bonjour,</p>

    <p>Vous avez passe <strong>{time_str}</strong> a explorer notre page audit gratuit.
    C'est que le monitoring de votre infrastructure est un sujet important pour vous.</p>

    <p><strong>Voici ce qu'on propose pour aller plus vite :</strong></p>

    <div style="background: #ecfdf5; padding: 20px; border-radius: 10px; border-left: 4px solid #059669; margin: 20px 0;">
        <p style="margin: 0 0 5px; font-weight: 700; color: #065f46; font-size: 1.1rem;">Option 1 : Essai gratuit 14 jours</p>
        <p style="margin: 0 0 12px; color: #374151;">10 monitors, checks toutes les 5min, alertes IA. Sans carte bancaire.</p>
        <a href="{TRIAL_14D_URL}?utm_source=post_visit_2h&utm_campaign=conversion_express" style="display: inline-block; background: linear-gradient(135deg, #059669, #047857); color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 700;">Demarrer mon essai gratuit</a>
    </div>

    <div style="background: #eff6ff; padding: 20px; border-radius: 10px; border-left: 4px solid #2563eb; margin: 20px 0;">
        <p style="margin: 0 0 5px; font-weight: 700; color: #1e40af; font-size: 1.1rem;">Option 2 : Abonnement Pro a 29EUR/mois</p>
        <p style="margin: 0 0 12px; color: #374151;">Monitors illimites, SMS alertes, API complete, rapports IA.</p>
        <a href="{CHECKOUT_STARTER_URL}" style="display: inline-block; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 700;">S'abonner maintenant</a>
    </div>

    <div style="background: #fef3c7; padding: 20px; border-radius: 10px; border-left: 4px solid #d97706; margin: 20px 0;">
        <p style="margin: 0 0 5px; font-weight: 700; color: #92400e; font-size: 1.1rem;">Option 3 : Appel decouverte 15min (gratuit)</p>
        <p style="margin: 0 0 12px; color: #374151;">On analyse votre setup ensemble et on identifie les quick wins.</p>
        <a href="{BOOKING_URL}?utm_source=post_visit_2h" style="display: inline-block; background: linear-gradient(135deg, #d97706, #b45309); color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 700;">Reserver 15 min</a>
    </div>

    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">

    <p style="color: #6b7280; font-size: 0.9rem;">
        <strong>Pourquoi ArkWatch ?</strong> Nos clients detectent les pannes en 30 secondes au lieu de 3 heures.
        L'IA resume chaque incident et vous donne un plan d'action.
    </p>

    <p>A bientot,<br><strong>L'equipe ArkForge</strong></p>
</div>

<div style="text-align: center; padding: 15px 0; color: #9ca3af; font-size: 12px;">
    <a href="https://arkforge.fr" style="color: #6366f1; text-decoration: none;">ArkForge</a> &bull;
    <a href="https://arkforge.fr/legal/privacy.html" style="color: #6366f1; text-decoration: none;">Confidentialite</a>
    <br><span style="font-size: 11px;">Vous recevez cet email car vous avez visite notre page audit gratuit.</span>
</div>
{tracking_pixel}
</body></html>"""

    text_body = (
        f"Bonjour,\n\n"
        f"Vous avez passe {time_str} sur notre page audit gratuit monitoring.\n"
        f"C'est que le monitoring de votre infrastructure est un sujet important.\n\n"
        f"Voici ce qu'on propose :\n\n"
        f"1. Essai gratuit 14 jours (sans CB) : {TRIAL_14D_URL}?utm_source=post_visit_2h\n"
        f"2. Abonnement Pro 29EUR/mois : {CHECKOUT_STARTER_URL}\n"
        f"3. Appel decouverte 15min gratuit : {BOOKING_URL}\n\n"
        f"Nos clients detectent les pannes en 30s au lieu de 3h.\n\n"
        f"L'equipe ArkForge"
    )

    return subject, text_body, html_body


def run():
    """Main execution: find eligible visitors, send commercial emails."""
    print(f"[POST-VISIT 2H] Starting run at {datetime.now(timezone.utc).isoformat()}")

    state = load_state()
    visitors = parse_visitors()
    eligible = find_eligible_visitors(visitors, state)

    if not eligible:
        print("[POST-VISIT 2H] No eligible visitors found")
        save_state(state)
        return {"sent": 0, "eligible": 0}

    print(f"[POST-VISIT 2H] Found {len(eligible)} eligible visitors")

    sent = 0
    for lead in eligible:
        subject, text_body, html_body = build_commercial_email(lead)

        if EMAIL_ENABLED:
            success = send_email(
                to_addr=lead["email"],
                subject=subject,
                body=text_body,
                html_body=html_body,
                reply_to="contact@arkforge.fr",
            )
        else:
            print(f"[DRY RUN] Would send to {lead['email']}")
            success = True

        if success:
            state["sent_visitor_ids"].append(lead["visitor_id"])
            state["total_sent"] = state.get("total_sent", 0) + 1
            sent += 1
            print(f"[POST-VISIT 2H] Sent to {lead['email']} (visitor: {lead['visitor_id']})")

    save_state(state)
    result = {"sent": sent, "eligible": len(eligible)}
    print(f"[POST-VISIT 2H] Done: {sent}/{len(eligible)} emails sent")
    return result


if __name__ == "__main__":
    run()
