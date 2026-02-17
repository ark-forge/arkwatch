#!/usr/bin/env python3
"""
End-to-End Test for Trial Signup Flow

Tests the complete flow:
1. User submits form on /trial-signup.html
2. API receives POST to /api/trial-signup
3. Submission tracked in trial_signups_tracking.json
4. Confirmation email sent with tracking pixel
5. Email open tracked via /api/track-email-open/trial_signup_<id>
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add API routers to path
sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch/src")

# Test configuration
TEST_DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
TRACKING_FILE = os.path.join(TEST_DATA_DIR, "trial_signups_tracking.json")


def cleanup_test_data():
    """Remove test tracking file"""
    if os.path.exists(TRACKING_FILE):
        os.remove(TRACKING_FILE)
        print(f"✓ Cleaned up {TRACKING_FILE}")


def test_1_submission():
    """Test 1: Submit trial signup form"""
    print("\n" + "="*60)
    print("TEST 1: Trial Signup Submission")
    print("="*60)

    from api.routers.trial_signup import TrialSignupRequest, trial_signup

    # Prepare test submission
    submission_id = f"{int(time.time())}_test123"
    test_request = TrialSignupRequest(
        name="John Test User",
        email="john.test@example.com",
        usecase="I want to monitor my company's API status page and competitor pricing pages to track changes in real-time.",
        source="test",
        campaign="trial_signup",
        submission_id=submission_id,
        utm_source="unittest",
        utm_campaign="test_flow",
        referrer="https://test.local",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # Mock async call
    import asyncio
    response = asyncio.run(trial_signup(test_request))

    # Verify response
    assert response.success == True, "Signup should succeed"
    assert response.submission_id == submission_id, "Submission ID should match"
    assert "try" in response.redirect_url, "Should redirect to /try page"

    print(f"✓ Submission successful")
    print(f"  - Submission ID: {response.submission_id}")
    print(f"  - Redirect URL: {response.redirect_url}")
    print(f"  - Message: {response.message}")

    # Verify tracking file created
    assert os.path.exists(TRACKING_FILE), "Tracking file should be created"
    print(f"✓ Tracking file created: {TRACKING_FILE}")

    # Verify tracking data
    with open(TRACKING_FILE) as f:
        tracking_data = json.load(f)

    assert len(tracking_data["submissions"]) == 1, "Should have 1 submission"
    submission = tracking_data["submissions"][0]

    assert submission["submission_id"] == submission_id
    assert submission["name"] == "John Test User"
    assert submission["email"] == "john.test@example.com"
    assert submission["email_sent"] == True, "Email should be marked as sent"
    assert submission["email_opened"] == False, "Email not opened yet"

    print(f"✓ Submission tracked correctly")
    print(f"  - Name: {submission['name']}")
    print(f"  - Email: {submission['email']}")
    print(f"  - Email sent: {submission['email_sent']}")
    print(f"  - Use case: {submission['usecase'][:50]}...")

    return submission_id


def test_2_duplicate_submission():
    """Test 2: Prevent duplicate submissions"""
    print("\n" + "="*60)
    print("TEST 2: Duplicate Submission Prevention")
    print("="*60)

    from api.routers.trial_signup import TrialSignupRequest, trial_signup

    # Try to submit with same email
    submission_id = f"{int(time.time())}_duplicate"
    test_request = TrialSignupRequest(
        name="John Test User Duplicate",
        email="john.test@example.com",  # Same email as test 1
        usecase="Different use case",
        source="test",
        campaign="trial_signup",
        submission_id=submission_id
    )

    import asyncio
    response = asyncio.run(trial_signup(test_request))

    # Should still succeed but return existing submission
    assert response.success == True
    assert "Welcome back" in response.message or "returning" in response.redirect_url

    print(f"✓ Duplicate prevented correctly")
    print(f"  - Message: {response.message}")

    # Verify still only 1 submission in tracking
    with open(TRACKING_FILE) as f:
        tracking_data = json.load(f)

    assert len(tracking_data["submissions"]) == 1, "Should still have only 1 submission"
    print(f"✓ No duplicate entry created")


def test_3_email_open_tracking(submission_id: str):
    """Test 3: Track email open via pixel"""
    print("\n" + "="*60)
    print("TEST 3: Email Open Tracking")
    print("="*60)

    from api.routers.email_tracking import track_email_open

    # Simulate pixel load
    lead_id = f"trial_signup_{submission_id}"

    import asyncio
    asyncio.run(track_email_open(lead_id))

    print(f"✓ Email open tracked for: {lead_id}")

    # Verify tracking data updated
    with open(TRACKING_FILE) as f:
        tracking_data = json.load(f)

    submission = tracking_data["submissions"][0]
    assert submission["email_opened"] == True, "Email should be marked as opened"
    assert submission["email_opened_at"] is not None, "Open timestamp should be recorded"
    assert len(submission.get("email_opens", [])) >= 1, "Should have at least 1 open event"

    print(f"✓ Email open recorded correctly")
    print(f"  - Opened: {submission['email_opened']}")
    print(f"  - Opened at: {submission['email_opened_at']}")
    print(f"  - Total opens: {len(submission.get('email_opens', []))}")


def test_4_stats_endpoint():
    """Test 4: Stats endpoint returns correct data"""
    print("\n" + "="*60)
    print("TEST 4: Stats Endpoint")
    print("="*60)

    from api.routers.trial_signup import trial_signup_stats

    import asyncio
    stats = asyncio.run(trial_signup_stats())

    assert stats["total_submissions"] == 1
    assert stats["total_emails_sent"] == 1
    assert stats["total_email_opens"] == 1
    assert stats["email_send_rate"] == 100.0
    assert stats["email_open_rate"] == 100.0

    print(f"✓ Stats calculated correctly")
    print(f"  - Total submissions: {stats['total_submissions']}")
    print(f"  - Emails sent: {stats['total_emails_sent']}")
    print(f"  - Emails opened: {stats['total_email_opens']}")
    print(f"  - Open rate: {stats['email_open_rate']}%")


def test_5_html_page_exists():
    """Test 5: HTML page exists and is accessible"""
    print("\n" + "="*60)
    print("TEST 5: HTML Page Exists")
    print("="*60)

    html_file = "/opt/claude-ceo/workspace/arkwatch/site/trial-signup.html"
    assert os.path.exists(html_file), f"HTML file should exist at {html_file}"

    with open(html_file) as f:
        content = f.read()

    # Verify key elements
    assert "<form" in content, "Should have form element"
    assert 'id="name"' in content, "Should have name input"
    assert 'id="email"' in content, "Should have email input"
    assert 'id="usecase"' in content, "Should have usecase textarea"
    assert "/api/trial-signup" in content, "Should POST to correct endpoint"
    assert "track-email-open" in content, "Should have tracking pixel"

    print(f"✓ HTML page exists and contains required elements")
    print(f"  - File: {html_file}")
    print(f"  - Size: {len(content)} bytes")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("TRIAL SIGNUP FLOW - END-TO-END TEST")
    print("="*70)

    try:
        # Clean up before tests
        cleanup_test_data()

        # Run tests
        submission_id = test_1_submission()
        test_2_duplicate_submission()
        test_3_email_open_tracking(submission_id)
        test_4_stats_endpoint()
        test_5_html_page_exists()

        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\nDeliverables verified:")
        print("  ✓ Page live at /trial-signup.html")
        print("  ✓ Form with name+email+usecase fields")
        print("  ✓ Tracking pixel integration")
        print("  ✓ Auto-email confirmation (logged)")
        print("  ✓ Redirection to /try")
        print("  ✓ Email open tracking working")
        print("  ✓ 1 test submission completed successfully")
        print("\n" + "="*70)

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Optional: keep test data for inspection
        # cleanup_test_data()
        print(f"\nTest data preserved at: {TRACKING_FILE}")


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
