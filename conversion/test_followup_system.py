#!/usr/bin/env python3
"""
Test script for automated trial follow-up system
Creates test signups at different stages and validates email sending logic
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# Paths
DATA_DIR = Path("/opt/claude-ceo/workspace/arkwatch/data")
TRIAL_SIGNUPS_FILE = DATA_DIR / "trial_signups_tracking.json"
FOLLOWUP_STATE_FILE = DATA_DIR / "trial_followup_state.json"


def create_test_signups():
    """Create test signups at different stages (J+1, J+3, J+7)."""
    now = datetime.utcnow()

    test_signups = {
        "campaign": "trial_signup",
        "created_at": now.isoformat() + "Z",
        "last_updated": now.isoformat() + "Z",
        "submissions": [
            # Should trigger J+1 email (signed up 1 day ago)
            {
                "submission_id": "test_day1_eligible",
                "name": "Alice Day1",
                "email": "alice-day1@testark.com",
                "usecase": "I want to monitor my SaaS landing page for downtime and price changes",
                "source": "test",
                "campaign": "trial_signup",
                "utm_source": None,
                "utm_campaign": None,
                "referrer": None,
                "submitted_at": (now - timedelta(days=1)).isoformat() + "Z",
                "email_sent": False,
                "email_sent_at": None,
                "email_opened": False,
                "email_opened_at": None,
                "conversion_completed": False,
                "conversion_completed_at": None
            },
            # Should trigger J+3 email (signed up 3 days ago)
            {
                "submission_id": "test_day3_eligible",
                "name": "Bob Day3",
                "email": "bob-day3@testark.com",
                "usecase": "Monitor my API status page and get alerts when incidents occur",
                "source": "test",
                "campaign": "trial_signup",
                "utm_source": "linkedin",
                "utm_campaign": "launch",
                "referrer": None,
                "submitted_at": (now - timedelta(days=3)).isoformat() + "Z",
                "email_sent": False,
                "email_sent_at": None,
                "email_opened": False,
                "email_opened_at": None,
                "conversion_completed": False,
                "conversion_completed_at": None
            },
            # Should trigger J+7 email (signed up 7 days ago)
            {
                "submission_id": "test_day7_eligible",
                "name": "Charlie Day7",
                "email": "charlie-day7@testark.com",
                "usecase": "Track competitor pricing and product changes automatically",
                "source": "test",
                "campaign": "trial_signup",
                "utm_source": "hackernews",
                "utm_campaign": "show_hn",
                "referrer": None,
                "submitted_at": (now - timedelta(days=7)).isoformat() + "Z",
                "email_sent": False,
                "email_sent_at": None,
                "email_opened": False,
                "email_opened_at": None,
                "conversion_completed": False,
                "conversion_completed_at": None
            },
            # Should NOT trigger (already converted)
            {
                "submission_id": "test_converted_skip",
                "name": "Diana Converted",
                "email": "diana-converted@testark.com",
                "usecase": "Monitor checkout flow",
                "source": "test",
                "campaign": "trial_signup",
                "utm_source": None,
                "utm_campaign": None,
                "referrer": None,
                "submitted_at": (now - timedelta(days=2)).isoformat() + "Z",
                "email_sent": False,
                "email_sent_at": None,
                "email_opened": False,
                "email_opened_at": None,
                "conversion_completed": True,  # Converted!
                "conversion_completed_at": (now - timedelta(hours=12)).isoformat() + "Z"
            },
            # Should NOT trigger (too recent, only 6 hours ago)
            {
                "submission_id": "test_too_recent",
                "name": "Eve Recent",
                "email": "eve-recent@testark.com",
                "usecase": "General monitoring",
                "source": "test",
                "campaign": "trial_signup",
                "utm_source": None,
                "utm_campaign": None,
                "referrer": None,
                "submitted_at": (now - timedelta(hours=6)).isoformat() + "Z",
                "email_sent": False,
                "email_sent_at": None,
                "email_opened": False,
                "email_opened_at": None,
                "conversion_completed": False,
                "conversion_completed_at": None
            }
        ],
        "metrics": {
            "total_submissions": 5,
            "total_emails_sent": 0,
            "total_conversions": 1,
            "conversion_rate": 20.0
        }
    }

    return test_signups


def backup_current_data():
    """Backup current data before test."""
    backup_suffix = f".backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if TRIAL_SIGNUPS_FILE.exists():
        backup = Path(str(TRIAL_SIGNUPS_FILE) + backup_suffix)
        with open(TRIAL_SIGNUPS_FILE) as f:
            data = f.read()
        with open(backup, "w") as f:
            f.write(data)
        print(f"✅ Backed up signups to {backup}")

    if FOLLOWUP_STATE_FILE.exists():
        backup = Path(str(FOLLOWUP_STATE_FILE) + backup_suffix)
        with open(FOLLOWUP_STATE_FILE) as f:
            data = f.read()
        with open(backup, "w") as f:
            f.write(data)
        print(f"✅ Backed up state to {backup}")


def write_test_data():
    """Write test signups to file."""
    test_data = create_test_signups()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(TRIAL_SIGNUPS_FILE, "w") as f:
        json.dump(test_data, f, indent=2)

    print(f"✅ Written test signups to {TRIAL_SIGNUPS_FILE}")
    print(f"\nTest scenarios:")
    print(f"  - Alice (J+1): Should receive onboarding tips")
    print(f"  - Bob (J+3): Should receive case study")
    print(f"  - Charlie (J+7): Should receive call offer")
    print(f"  - Diana (converted): Should be skipped")
    print(f"  - Eve (too recent): Should be skipped")


def show_expected_results():
    """Show expected test results."""
    print(f"\n📊 Expected results when running automated_trial_followup.py:")
    print(f"\n{'-'*60}")
    print(f"{'Email':<30} {'Sequence':<10} {'Should Send':<15}")
    print(f"{'-'*60}")
    print(f"{'alice-day1@testark.com':<30} {'day1':<10} {'YES (J+1)':<15}")
    print(f"{'bob-day3@testark.com':<30} {'day3':<10} {'YES (J+3)':<15}")
    print(f"{'charlie-day7@testark.com':<30} {'day7':<10} {'YES (J+7)':<15}")
    print(f"{'diana-converted@testark.com':<30} {'N/A':<10} {'NO (converted)':<15}")
    print(f"{'eve-recent@testark.com':<30} {'N/A':<10} {'NO (too recent)':<15}")
    print(f"{'-'*60}")
    print(f"\n✅ Expected: 3 emails sent (day1, day3, day7)")
    print(f"\n⚠️  Note: Warmup limit is 30/day, so 3 emails is safe")


def run_test():
    """Run test setup."""
    print("🧪 Setting up test environment for automated trial follow-up\n")

    # Backup current data
    backup_current_data()
    print()

    # Write test data
    write_test_data()

    # Show expected results
    show_expected_results()

    print(f"\n🚀 Ready to test! Run:")
    print(f"   cd /opt/claude-ceo/workspace/arkwatch/conversion")
    print(f"   python3 automated_trial_followup.py")
    print(f"\n📝 Then check:")
    print(f"   - trial_followup_state.json (should have 3 entries)")
    print(f"   - trial_followup_log.json (should have 3 send actions)")
    print(f"   - /opt/claude-ceo/workspace/memory/warmup_log.json (should have 3 sent emails)")
    print(f"\n🔄 To restore original data:")
    print(f"   mv {TRIAL_SIGNUPS_FILE}.backup_* {TRIAL_SIGNUPS_FILE}")
    print(f"   mv {FOLLOWUP_STATE_FILE}.backup_* {FOLLOWUP_STATE_FILE}")


if __name__ == "__main__":
    run_test()
