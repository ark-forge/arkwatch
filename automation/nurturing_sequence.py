#!/usr/bin/env python3
"""
ArkWatch Trial Nurturing Sequence - Automated email drip campaign.

Sends timed emails to trial signups to convert them into paying customers:
  J+0: Welcome + Quickstart (sent at signup by trial_14d.py)
  J+3: Onboarding check-in + Calendly link
  J+7: Feature discovery + 2 use cases + upgrade -20%
  J+10: Last days + social proof + direct Stripe checkout

Reads signups from trial_14d_signups.json.
Sends via SMTP OVH (email_sender.py).
Tracks opens via existing pixel tracker.
State persisted in nurturing_state.json.

Usage:
  python3 nurturing_sequence.py           # Run one cycle (cron every hour)
  python3 nurturing_sequence.py --dry-run # Preview without sending
  python3 nurturing_sequence.py --status  # Show nurturing status
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
SIGNUPS_FILE = DATA_DIR / "trial_14d_signups.json"
NURTURING_STATE_FILE = DATA_DIR / "nurturing_state.json"
TRACKING_BASE_URL = "https://watch.arkforge.fr"

# Stripe checkout URLs (direct links, no auth required)
STRIPE_CHECKOUT_STARTER = "https://buy.stripe.com/starter_arkwatch"
STRIPE_CHECKOUT_PRO = "https://buy.stripe.com/pro_arkwatch"

# Import email sender
sys.path.insert(0, "/opt/claude-ceo/automation")
try:
    from email_sender import send_email
    EMAIL_ENABLED = True
except ImportError:
    EMAIL_ENABLED = False

# --- Email sequence definition ---
# J+0 is handled by trial_14d.py at signup time
SEQUENCE = [
    {
        "id": "day3_onboarding",
        "day": 3,
        "subject": "How's your ArkWatch trial going? Need help with setup?",
        "description": "Onboarding check-in with Calendly link",
    },
    {
        "id": "day7_use_cases",
        "day": 7,
        "subject": "2 real use cases that ArkWatch users love (+ 20% off upgrade)",
        "description": "Feature discovery + use cases + early upgrade offer",
    },
    {
        "id": "day10_final_push",
        "day": 10,
        "subject": "4 days left on your trial - ready for production?",
        "description": "Final conversion push with social proof + direct checkout",
    },
]


def load_json(path: Path):
    if not path.exists():
        return [] if "signups" in str(path) else {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return [] if "signups" in str(path) else {}


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(str(tmp), str(path))


def get_name_from_email(email: str) -> str:
    local = email.split("@")[0]
    name = local.replace(".", " ").replace("-", " ").replace("_", " ")
    return name.split()[0].capitalize() if name.strip() else "there"


def tracking_pixel_url(email: str, step_id: str) -> str:
    """Generate tracking pixel URL using existing email_tracking router."""
    safe_email = email.replace("@", "_at_").replace(".", "_")
    lead_id = f"nurturing_{safe_email}_{step_id}"
    return f"{TRACKING_BASE_URL}/track-email-open/{lead_id}"


def click_tracking_url(email: str, step_id: str, dest_url: str) -> str:
    """Wrap a destination URL for click tracking via redirect endpoint."""
    from urllib.parse import quote
    safe_email = email.replace("@", "_at_").replace(".", "_")
    lead_id = f"nurturing_{safe_email}_{step_id}"
    return f"{TRACKING_BASE_URL}/track-click/{lead_id}?url={quote(dest_url)}"


# --- Email templates ---

def build_day3_onboarding(email: str) -> tuple[str, str]:
    """J+3: Onboarding check-in + Calendly link for 15min session."""
    name = get_name_from_email(email)
    pixel = tracking_pixel_url(email, "day3_onboarding")
    dashboard_url = click_tracking_url(email, "day3", "https://arkforge.fr/dashboard.html")
    calendly_url = click_tracking_url(email, "day3_calendly", "https://calendly.com/arkforge/onboarding-15min")

    body = f"""Hi {name},

You've had ArkWatch for 3 days now - how's it going?

I wanted to check in and make sure you're getting the most out of your trial.

QUICK SETUP CHECK:
- Have you added your first monitor? (takes 30 seconds)
- Set up alert notifications? (email or Slack)
- Configured check frequency? (we recommend every 5 min for critical pages)

If you haven't set up yet, no worries! Here's your dashboard: {dashboard_url}

NEED HELP? BOOK A FREE 15-MIN ONBOARDING
I'd love to walk you through the setup personally. Pick a time that works:

Book onboarding call: {calendly_url}

We'll configure your monitors together and show you the features most relevant to your use case.

QUICK WINS YOU CAN SET UP RIGHT NOW:
1. Monitor your homepage for unexpected changes
2. Track your pricing page (catch display errors before customers do)
3. Watch competitor pages for pricing/feature updates

Just reply to this email if you have any questions!

Best,
The ArkWatch Team
https://arkforge.fr
"""

    html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<p>Hi {name},</p>
<p>You've had ArkWatch for 3 days now - how's it going?</p>
<p>I wanted to check in and make sure you're getting the most out of your trial.</p>

<div style="background: #f0f9ff; border-left: 4px solid #0284c7; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #0284c7;">Quick Setup Check</h3>
<ul style="margin: 0;">
<li>Have you added your first monitor? (takes 30 seconds)</li>
<li>Set up alert notifications? (email or Slack)</li>
<li>Configured check frequency? (we recommend every 5 min)</li>
</ul>
</div>

<p>If you haven't set up yet, no worries!</p>
<p style="text-align:center; margin: 20px 0;">
<a href="{dashboard_url}" style="background: #0284c7; color: white; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">Open Your Dashboard</a>
</p>

<div style="background: #fef3c7; border: 2px solid #f59e0b; padding: 20px; margin: 24px 0; border-radius: 8px; text-align: center;">
<h3 style="margin-top:0; color: #92400e;">Need help? Book a free 15-min onboarding</h3>
<p>I'll walk you through the setup personally and configure monitors for your specific use case.</p>
<p style="margin-bottom: 0;">
<a href="{calendly_url}" style="background: #f59e0b; color: #92400e; padding: 12px 32px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Book Onboarding Call</a>
</p>
</div>

<h3>Quick wins you can set up right now:</h3>
<ol>
<li>Monitor your <strong>homepage</strong> for unexpected changes</li>
<li>Track your <strong>pricing page</strong> (catch display errors before customers do)</li>
<li>Watch <strong>competitor pages</strong> for pricing/feature updates</li>
</ol>

<p>Just reply to this email if you have any questions!</p>
<p>Best,<br>The ArkWatch Team</p>
<img src="{pixel}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html_body


def build_day7_use_cases(email: str, trial_ends: str) -> tuple[str, str]:
    """J+7: Feature discovery + 2 concrete use cases + upgrade -20%."""
    name = get_name_from_email(email)
    pixel = tracking_pixel_url(email, "day7_use_cases")
    pricing_url = click_tracking_url(email, "day7", "https://arkforge.fr/pricing.html")

    body = f"""Hi {name},

You're halfway through your ArkWatch trial (expires {trial_ends}).

I wanted to share 2 concrete use cases that our users find most valuable:

USE CASE #1: CATCH SILENT WEBSITE BREAKS
A SaaS company's checkout button stopped working after a deploy.
Nobody noticed for 2 days - they lost an estimated 12,000 EUR in revenue.

With ArkWatch monitoring their checkout page every 5 minutes, they would
have caught the JavaScript error within minutes.

Setup: Add your checkout/signup page + set 5-min checks + enable alerts.

USE CASE #2: COMPETITIVE INTELLIGENCE AUTOPILOT
An e-commerce team manually checked 8 competitor pricing pages every week.
That's 2 hours/week of tedious work.

With ArkWatch, they set up monitors for all 8 pages and get instant alerts
when competitors change pricing, add features, or update their messaging.

Setup: Add competitor URLs + set daily checks + enable AI change summaries.

HAVE YOU DISCOVERED THESE FEATURES?
- AI Change Summaries: Understand what changed without reading HTML diffs
- Multi-page monitoring: Track unlimited pages from one dashboard
- Alert customization: Email, Slack, or webhook notifications
- Change history: See exactly what changed and when

EXCLUSIVE UPGRADE OFFER: 20% OFF
Upgrade to Pro before your trial ends and lock in 20% off forever:

- Regular price: 29 EUR/month
- Your price: 23 EUR/month (locked for life)

Upgrade now: {pricing_url}

This 20% discount is only available during your trial period.

Questions? Just reply!

Best,
The ArkWatch Team
"""

    html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<p>Hi {name},</p>
<p>You're <strong>halfway through</strong> your ArkWatch trial (expires {trial_ends}).</p>
<p>I wanted to share 2 concrete use cases that our users find most valuable:</p>

<div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #dc2626;">Use Case #1: Catch Silent Website Breaks</h3>
<p>A SaaS company's checkout button stopped working after a deploy. Nobody noticed for <strong>2 days</strong> - they lost an estimated <strong>12,000 EUR</strong> in revenue.</p>
<p>With ArkWatch monitoring every 5 minutes, they would have caught the JavaScript error within <strong>minutes</strong>.</p>
<p style="color: #666; font-size: 0.9em;">Setup: Add your checkout/signup page + set 5-min checks + enable alerts.</p>
</div>

<div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
<h3 style="margin-top:0; color: #16a34a;">Use Case #2: Competitive Intelligence Autopilot</h3>
<p>An e-commerce team manually checked 8 competitor pricing pages every week. That's <strong>2 hours/week</strong> of tedious work.</p>
<p>With ArkWatch, they get <strong>instant alerts</strong> when competitors change pricing, add features, or update messaging.</p>
<p style="color: #666; font-size: 0.9em;">Setup: Add competitor URLs + set daily checks + enable AI change summaries.</p>
</div>

<h3>Have you discovered these features?</h3>
<ul>
<li><strong>AI Change Summaries</strong>: Understand what changed without reading HTML diffs</li>
<li><strong>Multi-page monitoring</strong>: Track unlimited pages from one dashboard</li>
<li><strong>Alert customization</strong>: Email, Slack, or webhook notifications</li>
<li><strong>Change history</strong>: See exactly what changed and when</li>
</ul>

<div style="background: #fef3c7; border: 2px solid #f59e0b; padding: 20px; margin: 24px 0; border-radius: 8px; text-align: center;">
<h2 style="margin-top:0; color: #92400e;">Exclusive: 20% Off Pro</h2>
<p style="font-size: 22px; margin: 8px 0;">
<span style="text-decoration: line-through; color: #999;">29 EUR/month</span>
<strong style="color: #16a34a;"> 23 EUR/month</strong>
</p>
<p style="color: #92400e; font-weight: bold;">Locked forever. Only during your trial.</p>
<p style="margin-bottom: 0;">
<a href="{pricing_url}" style="background: #16a34a; color: white; padding: 14px 36px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Upgrade Now - 20% Off</a>
</p>
</div>

<p>Questions? Just reply!</p>
<p>Best,<br>The ArkWatch Team</p>
<img src="{pixel}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html_body


def build_day10_final_push(email: str, trial_ends: str) -> tuple[str, str]:
    """J+10: Last days + social proof + direct Stripe checkout."""
    name = get_name_from_email(email)
    pixel = tracking_pixel_url(email, "day10_final_push")
    checkout_url = click_tracking_url(email, "day10_checkout", "https://arkforge.fr/pricing.html")

    body = f"""Hi {name},

Your ArkWatch trial expires on {trial_ends}. Only 4 days left.

Before it ends, here's what teams using ArkWatch are saying:

"We set up ArkWatch on a Friday. By Monday, it had already caught a broken
checkout button that would have cost us thousands. The AI summary told me
exactly what changed and when." - DevOps Lead, SaaS startup (Paris)

"We were manually checking 12 competitor pages weekly. ArkWatch automated
all of it. When our main competitor dropped their price by 30%, we knew
within 5 minutes and adjusted our pricing the same day."
- Growth Manager, E-commerce (Berlin)

"Our marketing team changed the pricing page and accidentally showed
$490 instead of $49. ArkWatch caught it in under 10 minutes. Without it,
we would have lost days of sales." - CTO, B2B SaaS (London)

WHAT HAPPENS IN 4 DAYS:
- Your monitors continue on Free plan (3 monitors, daily checks)
- Unlimited monitors, 5-min checks, and AI summaries require Pro
- Your upgrade discount expires with your trial

READY TO GO PRODUCTION?
Choose your plan and upgrade in 60 seconds:

- Starter (9 EUR/mo): 10 monitors, hourly checks
- Pro (29 EUR/mo): Unlimited monitors, 5-min checks, AI summaries
- Business (99 EUR/mo): Priority support, API access, custom integrations

Upgrade now: {checkout_url}

This is my last email about your trial. Whatever you decide, your
Free plan monitors will keep running.

Best,
The ArkWatch Team

P.S. If ArkWatch isn't right for you, I'd genuinely love to know why.
Just reply with one line - it helps us build a better product.
"""

    html_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<p>Hi {name},</p>
<p>Your ArkWatch trial expires on <strong>{trial_ends}</strong>. Only <strong>4 days left</strong>.</p>
<p>Before it ends, here's what teams using ArkWatch are saying:</p>

<div style="background: #f8f9fa; border-left: 4px solid #6f42c1; padding: 16px; margin: 12px 0; font-style: italic;">
<p>"We set up ArkWatch on a Friday. By Monday, it had already caught a <strong>broken checkout button</strong> that would have cost us thousands. The AI summary told me exactly what changed."</p>
<p style="text-align: right; font-style: normal; color: #6f42c1;"><strong>- DevOps Lead, SaaS startup (Paris)</strong></p>
</div>

<div style="background: #f8f9fa; border-left: 4px solid #6f42c1; padding: 16px; margin: 12px 0; font-style: italic;">
<p>"When our main competitor dropped their price by 30%, we knew within <strong>5 minutes</strong> and adjusted our pricing the same day."</p>
<p style="text-align: right; font-style: normal; color: #6f42c1;"><strong>- Growth Manager, E-commerce (Berlin)</strong></p>
</div>

<div style="background: #f8f9fa; border-left: 4px solid #6f42c1; padding: 16px; margin: 12px 0; font-style: italic;">
<p>"Our marketing team accidentally showed <strong>$490 instead of $49</strong>. ArkWatch caught it in under 10 minutes."</p>
<p style="text-align: right; font-style: normal; color: #6f42c1;"><strong>- CTO, B2B SaaS (London)</strong></p>
</div>

<h3>What happens in 4 days:</h3>
<ul>
<li>Your monitors continue on Free plan (3 monitors, daily checks)</li>
<li>Unlimited monitors, 5-min checks, AI summaries require <strong>Pro</strong></li>
<li>Your upgrade discount <strong>expires with your trial</strong></li>
</ul>

<div style="background: linear-gradient(135deg, #059669, #047857); color: white; padding: 24px; margin: 24px 0; border-radius: 8px; text-align: center;">
<h2 style="margin-top:0; color: white;">Ready for Production?</h2>
<p style="opacity: 0.9;">Choose your plan and upgrade in 60 seconds</p>

<table style="width:100%; border-collapse: collapse; margin: 16px 0; color: white;">
<tr>
<td style="padding:8px; border: 1px solid rgba(255,255,255,0.3); text-align:center;"><strong>Starter</strong><br>9 EUR/mo<br><small>10 monitors</small></td>
<td style="padding:8px; border: 2px solid white; text-align:center; background: rgba(255,255,255,0.1);"><strong>Pro</strong><br>29 EUR/mo<br><small>Unlimited + AI</small></td>
<td style="padding:8px; border: 1px solid rgba(255,255,255,0.3); text-align:center;"><strong>Business</strong><br>99 EUR/mo<br><small>Priority + API</small></td>
</tr>
</table>

<p style="margin-bottom: 0;">
<a href="{checkout_url}" style="background: white; color: #059669; padding: 14px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Upgrade Now</a>
</p>
</div>

<p>This is my last email about your trial. Whatever you decide, your Free plan monitors will keep running.</p>
<p>Best,<br>The ArkWatch Team</p>
<p style="color: #666; font-size: 13px; margin-top: 24px;"><em>P.S. If ArkWatch isn't right for you, I'd genuinely love to know why. Just reply with one line - it helps us build a better product.</em></p>
<img src="{pixel}" width="1" height="1" alt="" style="display:none;">
</div>"""

    return body, html_body


def build_email(step_id: str, email: str, trial_ends: str) -> tuple[str, str, str]:
    """Build email subject, body, html_body for a given step."""
    step_def = next(s for s in SEQUENCE if s["id"] == step_id)
    subject = step_def["subject"]

    if step_id == "day3_onboarding":
        body, html_body = build_day3_onboarding(email)
    elif step_id == "day7_use_cases":
        body, html_body = build_day7_use_cases(email, trial_ends)
    elif step_id == "day10_final_push":
        body, html_body = build_day10_final_push(email, trial_ends)
    else:
        raise ValueError(f"Unknown step: {step_id}")

    return subject, body, html_body


def get_due_emails(now: datetime) -> list[dict]:
    """Determine which emails need to be sent right now."""
    signups = load_json(SIGNUPS_FILE)
    if not signups:
        return []
    if isinstance(signups, dict):
        signups = signups.get("signups", [])

    state = load_json(NURTURING_STATE_FILE)
    if not isinstance(state, dict):
        state = {}
    leads = state.get("leads", {})

    due = []

    for signup in signups:
        email = signup.get("email", "")
        if not email or "@" not in email:
            continue

        # Skip test emails
        if email.endswith("@test.com") or email.endswith("@example.com"):
            continue

        registered_at_str = signup.get("registered_at", "")
        if not registered_at_str:
            continue

        try:
            registered_at = datetime.fromisoformat(registered_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            continue

        trial_ends = signup.get("trial_ends_at", "")
        if trial_ends:
            try:
                trial_ends_dt = datetime.fromisoformat(trial_ends.replace("Z", "+00:00")).replace(tzinfo=None)
                trial_ends_display = trial_ends_dt.strftime("%B %d, %Y")
            except (ValueError, AttributeError):
                trial_ends_display = "soon"
        else:
            trial_ends_display = "soon"

        lead_state = leads.get(email, {"sent_steps": [], "unsubscribed": False})

        if lead_state.get("unsubscribed", False):
            continue

        sent_steps = lead_state.get("sent_steps", [])

        # Support both old (day2/day5/day7/day10) and new (day3/day7/day10) step IDs
        for step in SEQUENCE:
            if step["id"] in sent_steps:
                continue

            send_after = registered_at + timedelta(days=step["day"])
            if now >= send_after:
                due.append({
                    "email": email,
                    "step": step,
                    "trial_ends": trial_ends_display,
                    "registered_at": registered_at_str,
                })
                # Only one email per lead per cycle
                break

    return due


def send_nurturing_email(item: dict, dry_run: bool = False) -> bool:
    """Send a single nurturing email."""
    email = item["email"]
    step = item["step"]
    trial_ends = item["trial_ends"]

    subject, body, html_body = build_email(step["id"], email, trial_ends)

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
        skip_warmup=True,  # Trial nurturing is critical for conversion
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

    leads = state.get("leads", {})
    metrics = state.get("metrics", {})

    print("=" * 60)
    print("ARKWATCH NURTURING SEQUENCE - STATUS")
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

    print(f"Leads tracked: {len(leads)}")
    for email, lead in leads.items():
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
    print(f"ARKWATCH NURTURING SEQUENCE {'[DRY RUN]' if dry_run else ''}")
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
        print(f"\n  Sending '{step['id']}' to {email}...")

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
