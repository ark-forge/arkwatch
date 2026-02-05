"""Simple API Key authentication"""
import secrets
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import json
import os

API_KEYS_FILE = "/opt/claude-ceo/workspace/arkwatch/data/api_keys.json"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _load_keys() -> dict:
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_keys(keys: dict):
    os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2, default=str)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_api_key(name: str, email: str, tier: str = "free") -> tuple[str, str]:
    """Create a new API key. Returns (raw_key, key_hash)."""
    keys = _load_keys()

    # Generate key
    raw_key = f"ak_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)

    keys[key_hash] = {
        "name": name,
        "email": email,
        "tier": tier,
        "created_at": datetime.utcnow().isoformat(),
        "last_used": None,
        "requests_count": 0,
        # Stripe fields
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "subscription_status": None,  # active, canceled, past_due, etc.
    }

    _save_keys(keys)
    return raw_key, key_hash


def update_stripe_info(
    key_hash: str,
    customer_id: str = None,
    subscription_id: str = None,
    subscription_status: str = None,
    tier: str = None
):
    """Update Stripe-related fields for an API key"""
    keys = _load_keys()

    if key_hash not in keys:
        return False

    if customer_id is not None:
        keys[key_hash]["stripe_customer_id"] = customer_id
    if subscription_id is not None:
        keys[key_hash]["stripe_subscription_id"] = subscription_id
    if subscription_status is not None:
        keys[key_hash]["subscription_status"] = subscription_status
    if tier is not None:
        keys[key_hash]["tier"] = tier

    _save_keys(keys)
    return True


def get_user_by_customer_id(customer_id: str) -> Optional[tuple[str, dict]]:
    """Find a user by their Stripe customer ID. Returns (key_hash, user_data)."""
    keys = _load_keys()

    for key_hash, user_data in keys.items():
        if user_data.get("stripe_customer_id") == customer_id:
            return key_hash, user_data

    return None


def get_user_by_email(email: str) -> Optional[tuple[str, dict]]:
    """Find a user by their email. Returns (key_hash, user_data)."""
    keys = _load_keys()

    for key_hash, user_data in keys.items():
        if user_data.get("email") == email:
            return key_hash, user_data

    return None


def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate an API key and return user info"""
    if not api_key:
        return None
    
    keys = _load_keys()
    key_hash = _hash_key(api_key)
    
    if key_hash not in keys:
        return None
    
    # Update last used
    keys[key_hash]["last_used"] = datetime.utcnow().isoformat()
    keys[key_hash]["requests_count"] += 1
    _save_keys(keys)
    
    return keys[key_hash]


def get_tier_limits(tier: str) -> dict:
    """Get limits for a tier"""
    tiers = {
        "free": {"max_watches": 3, "check_interval_min": 86400},  # 1/day
        "starter": {"max_watches": 10, "check_interval_min": 3600},  # 1/hour
        "pro": {"max_watches": 50, "check_interval_min": 300},  # 5 min
        "business": {"max_watches": 1000, "check_interval_min": 60},  # 1 min
    }
    return tiers.get(tier, tiers["free"])


async def get_current_user(api_key: str = Security(api_key_header)) -> dict:
    """Dependency to get current authenticated user"""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    user = validate_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user


async def get_optional_user(api_key: str = Security(api_key_header)) -> Optional[dict]:
    """Dependency for optional authentication"""
    if not api_key:
        return None
    return validate_api_key(api_key)


# CLI helpers
def list_api_keys() -> list:
    """List all API keys (for admin)"""
    keys = _load_keys()
    return [
        {
            "hash": k[:8] + "...",
            "name": v["name"],
            "email": v["email"],
            "tier": v["tier"],
            "created_at": v["created_at"],
            "requests_count": v["requests_count"],
            "stripe_customer_id": v.get("stripe_customer_id"),
            "subscription_status": v.get("subscription_status"),
        }
        for k, v in keys.items()
    ]


def get_key_hash_for_user(user: dict) -> Optional[str]:
    """Get the key hash for a user (needed for updates)"""
    keys = _load_keys()
    for key_hash, user_data in keys.items():
        if user_data.get("email") == user.get("email"):
            return key_hash
    return None


if __name__ == "__main__":
    # Create a test key
    import sys
    if len(sys.argv) > 1:
        name = sys.argv[1]
        email = sys.argv[2] if len(sys.argv) > 2 else "test@test.com"
        tier = sys.argv[3] if len(sys.argv) > 3 else "free"
        key = create_api_key(name, email, tier)
        print(f"Created API key for {name}: {key}")
    else:
        print("Usage: python auth.py <name> [email] [tier]")
        print("\nExisting keys:")
        for k in list_api_keys():
            print(f"  - {k['name']} ({k['email']}) - {k['tier']}")
