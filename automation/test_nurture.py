#!/usr/bin/env python3
"""
Test script for free_trial_nurture.py

Tests the nurture logic without sending actual emails.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the main module
import free_trial_nurture as nurture


def create_test_signup(days_ago: int, email: str) -> dict:
    """Create a test signup entry."""
    registered_at = datetime.utcnow() - timedelta(days=days_ago)
    return {
        "email": email,
        "registered_at": registered_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ip": "127.0.0.1",
        "source": "test",
        "campaign": "free_trial_6months",
        "user_agent": "test",
        "referer": "",
    }


def test_phase_detection():
    """Test that the correct phase is detected for each scenario."""
    print("=== Testing Phase Detection ===\n")

    # Mock send_email to avoid actual sending
    original_send_email = nurture.send_email
    nurture.send_email = lambda to, subject, body: True

    test_cases = [
        {
            "name": "New signup (J+0)",
            "signup": create_test_signup(0, "test-j0@example.com"),
            "expected": "welcome",
        },
        {
            "name": "Activation needed (J+2)",
            "signup": create_test_signup(2, "test-j2@example.com"),
            "expected": "activation",
        },
        {
            "name": "Engagement (J+7)",
            "signup": create_test_signup(7, "test-j7@example.com"),
            "expected": "engagement",
        },
        {
            "name": "Conversion (J+150)",
            "signup": create_test_signup(150, "test-j150@example.com"),
            "expected": "conversion",
        },
        {
            "name": "Trial expired (J+181)",
            "signup": create_test_signup(181, "test-expired@example.com"),
            "expected": "skip",
        },
    ]

    results = []
    for case in test_cases:
        result = nurture.process_signup(case["signup"])
        action = result.get("action", "unknown")
        passed = case["expected"] in action or (case["expected"] == "skip" and action == "skip")

        status = "✓ PASS" if passed else "✗ FAIL"
        results.append(passed)

        print(f"{status} - {case['name']}")
        print(f"  Expected: {case['expected']}")
        print(f"  Got: {action}")
        print()

    # Restore original function
    nurture.send_email = original_send_email

    # Summary
    total = len(results)
    passed = sum(results)
    print(f"=== Summary: {passed}/{total} tests passed ===\n")

    return passed == total


def test_duplicate_prevention():
    """Test that duplicate emails are not sent."""
    print("=== Testing Duplicate Prevention ===\n")

    # Mock send_email
    original_send_email = nurture.send_email
    nurture.send_email = lambda to, subject, body: True

    # Create a signup and process it twice
    signup = create_test_signup(0, "test-duplicate@example.com")

    # First process (should send welcome)
    result1 = nurture.process_signup(signup)
    action1 = result1.get("action", "unknown")

    # Second process (should skip)
    result2 = nurture.process_signup(signup)
    action2 = result2.get("action", "unknown")

    # Restore original function
    nurture.send_email = original_send_email

    passed = "welcome" in action1 and action2 == "skip"
    status = "✓ PASS" if passed else "✗ FAIL"

    print(f"{status} - Duplicate prevention")
    print(f"  First process: {action1}")
    print(f"  Second process: {action2}")
    print()

    return passed


def test_email_validation():
    """Test email validation."""
    print("=== Testing Email Validation ===\n")

    test_cases = [
        {"email": "valid@example.com", "expected": True},
        {"email": "invalid", "expected": False},
        {"email": "", "expected": False},
        {"email": "no@domain", "expected": False},
    ]

    results = []
    for case in test_cases:
        signup = create_test_signup(0, case["email"])
        result = nurture.process_signup(signup)
        action = result.get("action", "unknown")

        # Invalid emails should be skipped
        passed = (case["expected"] and action != "skip") or (not case["expected"] and action == "skip")
        results.append(passed)

        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - Email: {case['email']}")
        print(f"  Expected valid: {case['expected']}")
        print(f"  Action: {action}")
        print()

    total = len(results)
    passed_count = sum(results)
    print(f"=== Summary: {passed_count}/{total} tests passed ===\n")

    return passed_count == total


def main():
    """Run all tests."""
    print("=" * 60)
    print("FREE TRIAL NURTURE - TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        ("Phase Detection", test_phase_detection),
        ("Duplicate Prevention", test_duplicate_prevention),
        ("Email Validation", test_email_validation),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"TEST: {name}")
        print(f"{'=' * 60}\n")

        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"✗ ERROR: {e}\n")
            results.append((name, False))

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)

    print(f"\n{passed_count}/{total} test suites passed")

    return passed_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
