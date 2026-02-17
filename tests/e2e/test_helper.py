#!/usr/bin/env python3
"""Helper script for E2E tests - manages test accounts directly via internal API.

Usage:
    python3 test_helper.py create <email>  → prints JSON {api_key, verification_code}
    python3 test_helper.py cleanup <email> → deletes test user data
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.api.auth import create_api_key, delete_api_key_by_email
from src.storage import get_db


def create_test_user(email: str):
    """Create a test user and return raw API key + raw verification code."""
    raw_key, key_hash, verification_code = create_api_key(
        name="E2E Test User",
        email=email,
        tier="free",
        privacy_accepted=True,
        client_ip="127.0.0.1",
    )
    return {
        "api_key": raw_key,
        "verification_code": verification_code,
    }


def cleanup_test_user(email: str):
    """Delete all data for a test user."""
    db = get_db()
    db.delete_user_data(email)
    delete_api_key_by_email(email)
    return {"status": "cleaned"}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 test_helper.py <create|cleanup> <email>", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]
    email = sys.argv[2]

    if action == "create":
        result = create_test_user(email)
        print(json.dumps(result))
    elif action == "cleanup":
        result = cleanup_test_user(email)
        print(json.dumps(result))
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)
