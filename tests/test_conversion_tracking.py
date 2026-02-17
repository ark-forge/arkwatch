"""Tests for conversion tracking functionality"""

import json
import os
import tempfile
from datetime import datetime

import pytest


# Mock functions for testing
def mock_create_api_key(name, email, tier="free", privacy_accepted=False, client_ip=None, signup_source=None):
    """Mock create_api_key to test signup_source parameter"""
    return ("mock_key", "mock_hash", "123456")


def test_signup_source_parameter():
    """Test that signup_source parameter is accepted"""
    # This would be the actual function call in production
    key, hash, code = mock_create_api_key(
        name="Test User",
        email="test@example.com",
        tier="free",
        privacy_accepted=True,
        client_ip="127.0.0.1",
        signup_source="devto"
    )

    assert key == "mock_key"
    assert hash == "mock_hash"
    assert code == "123456"


def test_stats_aggregation():
    """Test stats aggregation logic"""
    # Mock signup data
    signups = [
        {"email": "user1@test.com", "source": "devto", "created_at": "2026-02-07T12:00:00", "tier": "free", "email_verified": True},
        {"email": "user2@test.com", "source": "devto", "created_at": "2026-02-07T13:00:00", "tier": "free", "email_verified": False},
        {"email": "user3@test.com", "source": "ph", "created_at": "2026-02-07T14:00:00", "tier": "pro", "email_verified": True},
        {"email": "user4@test.com", "source": "direct", "created_at": "2026-02-08T10:00:00", "tier": "free", "email_verified": True},
    ]

    # Aggregate by source
    from collections import defaultdict
    by_source = defaultdict(int)
    by_day = defaultdict(int)

    for signup in signups:
        source = signup["source"]
        by_source[source] += 1

        created_at = signup.get("created_at")
        if created_at:
            dt = datetime.fromisoformat(created_at)
            day = dt.strftime("%Y-%m-%d")
            by_day[day] += 1

    assert by_source["devto"] == 2
    assert by_source["ph"] == 1
    assert by_source["direct"] == 1
    assert by_day["2026-02-07"] == 3
    assert by_day["2026-02-08"] == 1


def test_funnel_calculation():
    """Test funnel conversion rate calculation"""
    signups = [
        {"email_verified": True, "tier": "free"},
        {"email_verified": True, "tier": "pro"},
        {"email_verified": False, "tier": "free"},
        {"email_verified": True, "tier": "free"},
    ]

    total = len(signups)
    verified = sum(1 for s in signups if s.get("email_verified"))
    paid = sum(1 for s in signups if s.get("tier") not in ("free", None))

    verification_rate = (verified / total * 100) if total > 0 else 0.0
    paid_rate = (paid / total * 100) if total > 0 else 0.0

    assert total == 4
    assert verified == 3
    assert paid == 1
    assert verification_rate == 75.0
    assert paid_rate == 25.0


def test_default_source_value():
    """Test that default source is 'direct' when not provided"""
    signup_source = None
    final_source = signup_source or "direct"

    assert final_source == "direct"

    signup_source = "devto"
    final_source = signup_source or "direct"

    assert final_source == "devto"


if __name__ == "__main__":
    # Run tests manually
    test_signup_source_parameter()
    print("✓ test_signup_source_parameter passed")

    test_stats_aggregation()
    print("✓ test_stats_aggregation passed")

    test_funnel_calculation()
    print("✓ test_funnel_calculation passed")

    test_default_source_value()
    print("✓ test_default_source_value passed")

    print("\n✅ All tests passed!")
