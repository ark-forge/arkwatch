#!/usr/bin/env python3
"""
HOT SIGNAL RELANCE - Automation email contextuel sous 5min
Détecte visites /trial-14d, /pricing, /demo et envoie email contextuel
si le visiteur est un lead connu (email en DB).

FONDATIONS TASK #282 - 2026-02-11
Cron: */5 * * * * (toutes les 5 minutes)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import email sender
sys.path.insert(0, "/opt/claude-ceo/automation")
from email_sender import send_email

# === CONFIGURATION ===
# Pages hot à surveiller
HOT_PAGES = ["/trial-14d", "/pricing", "/demo", "/try", "/pricing-v2",
             "/audit-gratuit-monitoring", "/trial-signup"]

# Fenêtre de détection: visites des dernières 5 minutes
DETECTION_WINDOW_MINUTES = 5

# Cooldown: 1 email max par lead par 24h
COOLDOWN_HOURS = 24

# === PATHS ===
PAGE_VISITS_LOG = "/opt/claude-ceo/workspace/arkwatch/data/page_visits.jsonl"
TRIAL_14D_VISITORS = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_visitors.jsonl"
AUDIT_VISITORS = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_visitors.jsonl"

# Lead databases
TRIAL_SIGNUPS = "/opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json"
TRIAL_14D_SIGNUPS = "/opt/claude-ceo/workspace/arkwatch/data/trial_14d_signups.json"
DEMO_LEADS = "/opt/claude-ceo/workspace/arkwatch/data/demo_leads.json"
NURTURING_STATE = "/opt/claude-ceo/workspace/arkwatch/data/nurturing_audit_gratuit_state.json"
EMAIL_CONVERSATIONS = "/opt/claude-ceo/shareholder/email_conversations.json"

# State & tracking
STATE_FILE = "/opt/claude-ceo/workspace/arkwatch/data/hot_signal_relance_state.json"
TRACKING_LOG = "/opt/claude-ceo/workspace/arkwatch/data/hot_signal_relance_log.jsonl"

# API base URL for tracking
API_BASE = "https://watch.arkforge.fr"


def load_state():
    """Load relance state (cooldowns, sent emails)"""
    if Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {
        "last_run": None,
        "total_emails_sent": 0,
        "emails_sent": {},  # {email: last_sent_iso}
    }


def save_state(state):
    """Save state atomically"""
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(STATE_FILE).with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_FILE)


def log_relance(entry):
    """Append to relance tracking log"""
    Path(TRACKING_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def build_ip_to_email_map():
    """Build mapping IP → email from all lead databases"""
    ip_map = {}  # {ip: {email, name, source}}

    # 1. Trial 14-day signups (have IP + email)
    if Path(TRIAL_14D_SIGNUPS).exists():
        try:
            with open(TRIAL_14D_SIGNUPS) as f:
                signups = json.load(f)
            for s in signups:
                ip = s.get("ip")
                email = s.get("email")
                if ip and email:
                    ip_map[ip] = {
                        "email": email,
                        "name": email.split("@")[0],
                        "source": "trial_14d_signup"
                    }
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # 2. Trial signup tracking (has email but no IP directly - use submission data)
    if Path(TRIAL_SIGNUPS).exists():
        try:
            with open(TRIAL_SIGNUPS) as f:
                data = json.load(f)
            for s in data.get("submissions", []):
                email = s.get("email")
                name = s.get("name", "")
                if email:
                    # No IP in this DB, but keep for email lookup
                    pass
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # 3. Demo leads (have IP + email)
    if Path(DEMO_LEADS).exists():
        try:
            with open(DEMO_LEADS) as f:
                leads = json.load(f)
            for lead in leads:
                ip = lead.get("ip")
                email = lead.get("email")
                if ip and email:
                    ip_map[ip] = {
                        "email": email,
                        "name": email.split("@")[0],
                        "source": "demo_lead"
                    }
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # 4. Nurturing audit gratuit (has emails)
    if Path(NURTURING_STATE).exists():
        try:
            with open(NURTURING_STATE) as f:
                data = json.load(f)
            # These don't have IPs, but keep for reference
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    return ip_map


def get_all_known_emails():
    """Get set of all known lead emails from all databases"""
    emails = set()

    # Trial 14d signups
    if Path(TRIAL_14D_SIGNUPS).exists():
        try:
            with open(TRIAL_14D_SIGNUPS) as f:
                for s in json.load(f):
                    if s.get("email"):
                        emails.add(s["email"].lower())
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Trial signup tracking
    if Path(TRIAL_SIGNUPS).exists():
        try:
            with open(TRIAL_SIGNUPS) as f:
                for s in json.load(f).get("submissions", []):
                    if s.get("email"):
                        emails.add(s["email"].lower())
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Demo leads
    if Path(DEMO_LEADS).exists():
        try:
            with open(DEMO_LEADS) as f:
                for lead in json.load(f):
                    if lead.get("email"):
                        emails.add(lead["email"].lower())
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Nurturing audit gratuit leads
    if Path(NURTURING_STATE).exists():
        try:
            with open(NURTURING_STATE) as f:
                data = json.load(f)
            for email in data.get("leads", {}).keys():
                emails.add(email.lower())
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    return emails


def get_recent_hot_visits(window_minutes=5):
    """Get page visits from the last N minutes on hot pages"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)
    visits = []

    if not Path(PAGE_VISITS_LOG).exists():
        return visits

    try:
        with open(PAGE_VISITS_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                page = event.get("page", "")
                timestamp_str = event.get("timestamp", "")

                # Check if page is hot
                if not any(page.startswith(hp) or page == hp for hp in HOT_PAGES):
                    continue

                # Parse timestamp
                try:
                    ts = datetime.fromisoformat(timestamp_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                # Check if within window
                if ts >= cutoff:
                    visits.append({
                        "timestamp": timestamp_str,
                        "page": page,
                        "ip": event.get("ip", "unknown"),
                        "user_agent": event.get("user_agent", ""),
                        "referrer": event.get("referrer", ""),
                        "utm_source": event.get("utm_source"),
                        "utm_campaign": event.get("utm_campaign"),
                    })
    except Exception as e:
        print(f"ERROR reading page visits: {e}")

    return visits


def is_bot(user_agent):
    """Filter out bots/crawlers"""
    bot_patterns = ["googlebot", "bingbot", "slurp", "duckduckbot",
                    "baiduspider", "yandexbot", "facebot", "curl/",
                    "wget", "python-requests", "scrapy", "ahrefsbot",
                    "semrushbot", "dotbot", "mj12bot"]
    ua_lower = (user_agent or "").lower()
    return any(bot in ua_lower for bot in bot_patterns)


def check_cooldown(state, email):
    """Check if email is in cooldown (24h since last relance)"""
    last_sent = state.get("emails_sent", {}).get(email)
    if not last_sent:
        return False  # No cooldown

    try:
        last_dt = datetime.fromisoformat(last_sent)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        return elapsed < COOLDOWN_HOURS * 3600
    except (ValueError, TypeError):
        return False


def get_page_context(page):
    """Get contextual info for email template based on page visited"""
    contexts = {
        "/pricing": {
            "page_name": "notre page tarifs",
            "interest": "nos offres de monitoring",
            "cta_text": "Planifier une d\u00e9mo personnalis\u00e9e",
            "cta_url": f"{API_BASE}/demo.html",
            "subject": "Besoin d'aide pour choisir votre plan ArkWatch ?",
        },
        "/pricing-v2": {
            "page_name": "notre page tarifs",
            "interest": "nos offres de monitoring",
            "cta_text": "Planifier une d\u00e9mo personnalis\u00e9e",
            "cta_url": f"{API_BASE}/demo.html",
            "subject": "Besoin d'aide pour choisir votre plan ArkWatch ?",
        },
        "/trial-14d": {
            "page_name": "l'essai gratuit 14 jours",
            "interest": "tester ArkWatch",
            "cta_text": "D\u00e9marrer votre essai gratuit",
            "cta_url": f"{API_BASE}/trial-14d.html",
            "subject": "Votre essai ArkWatch vous attend",
        },
        "/try": {
            "page_name": "notre page d'essai",
            "interest": "essayer ArkWatch",
            "cta_text": "D\u00e9marrer votre essai gratuit",
            "cta_url": f"{API_BASE}/trial-14d.html",
            "subject": "Votre essai ArkWatch vous attend",
        },
        "/trial-signup": {
            "page_name": "l'inscription trial",
            "interest": "d\u00e9marrer un essai",
            "cta_text": "Finaliser votre inscription",
            "cta_url": f"{API_BASE}/trial-signup.html",
            "subject": "Finalisez votre inscription ArkWatch",
        },
        "/demo": {
            "page_name": "notre d\u00e9mo",
            "interest": "voir ArkWatch en action",
            "cta_text": "R\u00e9server votre cr\u00e9neau d\u00e9mo",
            "cta_url": f"{API_BASE}/demo.html",
            "subject": "Votre d\u00e9mo ArkWatch personnalis\u00e9e",
        },
        "/audit-gratuit-monitoring": {
            "page_name": "l'audit gratuit",
            "interest": "un audit de votre monitoring",
            "cta_text": "Obtenir votre audit gratuit",
            "cta_url": f"{API_BASE}/audit-gratuit-monitoring.html",
            "subject": "Votre audit monitoring gratuit est pr\u00eat",
        },
    }

    # Match the most specific page first
    for key in sorted(contexts.keys(), key=len, reverse=True):
        if page.startswith(key) or page == key:
            return contexts[key]

    # Fallback
    return {
        "page_name": "notre site",
        "interest": "ArkWatch",
        "cta_text": "En savoir plus",
        "cta_url": f"{API_BASE}",
        "subject": "ArkWatch - On peut vous aider ?",
    }


def build_contextual_email(email, page, context, tracking_id):
    """Build contextual HTML email based on page visited"""
    name = email.split("@")[0].replace(".", " ").replace("-", " ").title()

    tracking_pixel = f"{API_BASE}/track-email-open/{tracking_id}"
    cta_tracked = f"{API_BASE}/track-click/{tracking_id}?url={context['cta_url']}"

    # Plain text version
    plain_text = f"""Bonjour {name},

J'ai remarqu\u00e9 que vous consultiez {context['page_name']} il y a quelques instants.

Avez-vous des questions sur {context['interest']} ? Je serais ravi de vous aider \u00e0 trouver la solution la plus adapt\u00e9e \u00e0 vos besoins.

{context['cta_text']} : {context['cta_url']}

Vous pouvez \u00e9galement r\u00e9pondre directement \u00e0 cet email si vous avez la moindre question.

\u00c0 bient\u00f4t,
L'\u00e9quipe ArkForge
contact@arkforge.fr
"""

    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">

<p>Bonjour {name},</p>

<p>J'ai remarqu\u00e9 que vous consultiez <strong>{context['page_name']}</strong> il y a quelques instants.</p>

<p>Avez-vous des questions sur {context['interest']} ? Je serais ravi de vous aider \u00e0 trouver la solution la plus adapt\u00e9e \u00e0 vos besoins.</p>

<p style="text-align: center; margin: 30px 0;">
  <a href="{cta_tracked}" style="display: inline-block; background-color: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">{context['cta_text']}</a>
</p>

<p>Vous pouvez \u00e9galement r\u00e9pondre directement \u00e0 cet email si vous avez la moindre question.</p>

<p style="margin-top: 30px;">
\u00c0 bient\u00f4t,<br>
<strong>L'\u00e9quipe ArkForge</strong><br>
<span style="color: #666;">contact@arkforge.fr</span>
</p>

<hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
<p style="font-size: 11px; color: #999;">
Vous recevez cet email car vous avez visit\u00e9 arkforge.fr.
<a href="mailto:contact@arkforge.fr?subject=unsubscribe" style="color: #999;">Se d\u00e9sabonner</a>
</p>

<img src="{tracking_pixel}" width="1" height="1" style="display:none;" alt="">
</body>
</html>"""

    return plain_text, html_body


def run_hot_signal_relance():
    """Main relance logic: detect hot visits → match leads → send contextual email"""
    print(f"[{datetime.now(timezone.utc).isoformat()}] HOT SIGNAL RELANCE - Starting...")

    state = load_state()

    # 1. Build IP → email mapping
    ip_map = build_ip_to_email_map()
    all_emails = get_all_known_emails()
    print(f"  Known IPs: {len(ip_map)} | Known emails: {len(all_emails)}")

    # 2. Get recent hot page visits (last 5 min)
    recent_visits = get_recent_hot_visits(DETECTION_WINDOW_MINUTES)
    print(f"  Recent hot visits (last {DETECTION_WINDOW_MINUTES}min): {len(recent_visits)}")

    if not recent_visits:
        print("  No recent hot visits. Done.")
        save_state(state)
        return 0

    # 3. Match visits to known leads
    emails_sent = 0
    emails_skipped_cooldown = 0
    emails_skipped_bot = 0
    emails_skipped_unknown = 0

    for visit in recent_visits:
        ip = visit["ip"]
        page = visit["page"]
        user_agent = visit.get("user_agent", "")

        # Filter bots
        if is_bot(user_agent):
            emails_skipped_bot += 1
            continue

        # Look up IP in lead database
        lead = ip_map.get(ip)
        if not lead:
            emails_skipped_unknown += 1
            continue

        email = lead["email"]

        # Skip test emails
        if "test" in email.lower() or "example.com" in email.lower():
            emails_skipped_unknown += 1
            continue

        # Check cooldown
        if check_cooldown(state, email):
            emails_skipped_cooldown += 1
            print(f"  COOLDOWN: {email} (already emailed in last {COOLDOWN_HOURS}h)")
            continue

        # Build contextual email
        context = get_page_context(page)
        tracking_id = f"hot_relance_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}_{email.split('@')[0]}"

        plain_text, html_body = build_contextual_email(email, page, context, tracking_id)

        # Send email
        print(f"  SENDING to {email} (visited {page})...")
        success = send_email(
            to_addr=email,
            subject=context["subject"],
            body=plain_text,
            html_body=html_body,
            skip_warmup=True  # Hot signals bypass warmup (time-critical)
        )

        if success:
            emails_sent += 1
            state.setdefault("emails_sent", {})[email] = datetime.now(timezone.utc).isoformat()
            state["total_emails_sent"] = state.get("total_emails_sent", 0) + 1

            # Log relance
            log_relance({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "email": email,
                "page": page,
                "ip": ip,
                "tracking_id": tracking_id,
                "subject": context["subject"],
                "status": "sent",
                "source": lead.get("source", "unknown"),
            })
            print(f"  ✓ Email sent to {email}")
        else:
            log_relance({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "email": email,
                "page": page,
                "ip": ip,
                "tracking_id": tracking_id,
                "status": "failed",
            })
            print(f"  ✗ Failed to send to {email}")

    # Save state
    save_state(state)

    # Summary
    print(f"\n  === SUMMARY ===")
    print(f"  Emails sent: {emails_sent}")
    print(f"  Skipped (cooldown): {emails_skipped_cooldown}")
    print(f"  Skipped (bot): {emails_skipped_bot}")
    print(f"  Skipped (unknown IP): {emails_skipped_unknown}")
    print(f"  Total sent all-time: {state.get('total_emails_sent', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(run_hot_signal_relance())
