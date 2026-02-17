#!/usr/bin/env python3
"""
Quick status check for Free Trial Nurture System

Shows key metrics and recent activity.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# Paths
BASE_DIR = Path("/opt/claude-ceo/workspace/arkwatch")
DATA_DIR = BASE_DIR / "data"
SIGNUPS_FILE = DATA_DIR / "free_trial_signups.json"
API_KEYS_FILE = DATA_DIR / "api_keys.json"
WATCHES_FILE = DATA_DIR / "watches.json"
NURTURE_LOG_FILE = DATA_DIR / "nurture_log.json"


def load_json(filepath: Path) -> list | dict:
    """Load JSON file safely."""
    if not filepath.exists():
        return []
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def main():
    """Generate status report."""
    print("=" * 70)
    print("FREE TRIAL NURTURE SYSTEM - STATUS REPORT")
    print("=" * 70)
    print()

    # Load data
    signups = load_json(SIGNUPS_FILE)
    api_keys = load_json(API_KEYS_FILE)
    watches = load_json(WATCHES_FILE)
    nurture_logs = load_json(NURTURE_LOG_FILE)

    # Calculate metrics
    total_signups = len(signups)
    total_logs = len(nurture_logs)

    # Count events by type
    event_counts = {}
    for log in nurture_logs:
        for event in log.get("events", []):
            event_type = event.get("type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

    # Active users
    # Note: emails are encrypted in api_keys/watches, so we use simple counts
    # For accurate cross-referencing, use the full nurture script

    # api_keys is a dict, need to get values
    api_keys_list = list(api_keys.values()) if isinstance(api_keys, dict) else api_keys
    activated = len([k for k in api_keys_list if "email" in k or "user_email" in k])
    with_watches = len([w for w in watches if "user_email" in w or "notify_email" in w])

    # Recent signups (last 7 days)
    now = datetime.now().replace(tzinfo=None)
    recent_signups = 0
    for signup in signups:
        try:
            registered_str = signup.get("registered_at", "").replace("Z", "")
            registered = datetime.fromisoformat(registered_str)
            if (now - registered).days <= 7:
                recent_signups += 1
        except (ValueError, AttributeError):
            pass

    # Print report
    print("📊 SIGNUPS & ACTIVATION")
    print("-" * 70)
    print(f"  Total signups:            {total_signups}")
    print(f"  Recent signups (7d):      {recent_signups}")
    print(f"  Activated accounts:       {activated} ({activated/total_signups*100 if total_signups else 0:.1f}%)")
    print(f"  With watches created:     {with_watches} ({with_watches/total_signups*100 if total_signups else 0:.1f}%)")
    print()

    print("📧 NURTURE EMAILS")
    print("-" * 70)
    print(f"  Total users with emails:  {total_logs}")
    print()
    print("  Events by type:")
    for event_type, count in sorted(event_counts.items()):
        print(f"    - {event_type:30s} {count:3d}")
    print()

    print("🔄 FUNNEL CONVERSION")
    print("-" * 70)
    if total_signups > 0:
        activation_rate = activated / total_signups * 100
        engagement_rate = with_watches / activated * 100 if activated > 0 else 0

        print(f"  Signup → Activation:      {activation_rate:.1f}%")
        print(f"  Activation → Engagement:  {engagement_rate:.1f}%")
        print()

        # Targets
        print("  Targets:")
        print(f"    Activation:  >60%  {'✓' if activation_rate >= 60 else '✗'}")
        print(f"    Engagement:  >40%  {'✓' if engagement_rate >= 40 else '✗'}")
    else:
        print("  No data yet")

    print()

    # Recent activity
    print("🕐 RECENT ACTIVITY (Last 24h)")
    print("-" * 70)

    recent_events = []
    cutoff = now - timedelta(hours=24)

    for log in nurture_logs:
        for event in log.get("events", []):
            try:
                event_time_str = event.get("timestamp", "").replace("Z", "")
                event_time = datetime.fromisoformat(event_time_str)
                if event_time >= cutoff:
                    recent_events.append({
                        "email": log.get("email", "unknown"),
                        "type": event.get("type", "unknown"),
                        "time": event_time,
                    })
            except (ValueError, AttributeError):
                pass

    recent_events.sort(key=lambda x: x["time"], reverse=True)

    if recent_events:
        for event in recent_events[:10]:
            time_str = event["time"].strftime("%H:%M:%S")
            print(f"  {time_str} - {event['type']:30s} ({event['email']})")
    else:
        print("  No recent activity")

    print()
    print("=" * 70)
    print(f"Report generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
