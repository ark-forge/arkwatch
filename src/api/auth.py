"""Simple API Key authentication with email verification"""

import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from ..crypto import decrypt_pii, encrypt_pii

API_KEYS_FILE = "/opt/claude-ceo/workspace/arkwatch/data/api_keys.json"
_UNSUBSCRIBE_SECRET = os.getenv("ARKWATCH_UNSUBSCRIBE_SECRET", "arkwatch-unsubscribe-default-secret")

logger = logging.getLogger(__name__)

# PII fields that must be encrypted at rest
_PII_FIELDS = ("email", "name", "privacy_accepted_ip")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _decrypt_user_data(user_data: dict) -> dict:
    """Decrypt PII fields in user data for in-memory use."""
    result = dict(user_data)
    for field in _PII_FIELDS:
        if field in result and result[field] and isinstance(result[field], str):
            result[field] = decrypt_pii(result[field])
    return result


def _encrypt_user_data(user_data: dict) -> dict:
    """Encrypt PII fields in user data for storage."""
    result = dict(user_data)
    for field in _PII_FIELDS:
        if field in result and result[field] and isinstance(result[field], str):
            result[field] = encrypt_pii(result[field])
    return result


def _load_keys() -> dict:
    """Load and decrypt API keys from disk."""
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE) as f:
            raw = json.load(f)
        # Decrypt PII fields in memory
        return {k: _decrypt_user_data(v) for k, v in raw.items()}
    return {}


def _save_keys(keys: dict):
    """Encrypt PII fields and save to disk."""
    os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
    # Encrypt PII fields before writing
    encrypted = {k: _encrypt_user_data(v) for k, v in keys.items()}
    with open(API_KEYS_FILE, "w") as f:
        json.dump(encrypted, f, indent=2, default=str)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_api_key(
    name: str,
    email: str,
    tier: str = "free",
    is_admin: bool = False,
    privacy_accepted: bool = False,
    client_ip: str = None,
    signup_source: str = None,
) -> tuple[str, str, str]:
    """Create a new API key. Returns (raw_key, key_hash, verification_code)."""
    keys = _load_keys()

    # Generate key
    raw_key = f"ak_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)

    # Generate 6-digit verification code (valid 24h)
    verification_code = f"{secrets.randbelow(900000) + 100000}"
    verification_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    now = datetime.utcnow().isoformat()

    keys[key_hash] = {
        "name": name,
        "email": email,
        "tier": tier,
        "is_admin": is_admin,
        "email_verified": False,
        "verification_code": hashlib.sha256(verification_code.encode()).hexdigest(),
        "verification_expires": verification_expires,
        "created_at": now,
        "last_used": None,
        "requests_count": 0,
        # RGPD consent tracking
        "privacy_accepted": privacy_accepted,
        "privacy_accepted_at": now if privacy_accepted else None,
        "privacy_accepted_ip": client_ip,
        # Stripe fields
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "subscription_status": None,  # active, canceled, past_due, etc.
        # Conversion tracking
        "signup_source": signup_source or "direct",
    }

    _save_keys(keys)
    return raw_key, key_hash, verification_code


def update_stripe_info(
    key_hash: str,
    customer_id: str = None,
    subscription_id: str = None,
    subscription_status: str = None,
    tier: str = None,
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


def get_user_by_customer_id(customer_id: str) -> tuple[str, dict] | None:
    """Find a user by their Stripe customer ID. Returns (key_hash, user_data)."""
    keys = _load_keys()

    for key_hash, user_data in keys.items():
        if user_data.get("stripe_customer_id") == customer_id:
            return key_hash, user_data

    return None


def get_user_by_email(email: str) -> tuple[str, dict] | None:
    """Find a user by their email. Returns (key_hash, user_data)."""
    keys = _load_keys()

    for key_hash, user_data in keys.items():
        if user_data.get("email") == email:
            return key_hash, user_data

    return None


def validate_api_key(api_key: str) -> dict | None:
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


def update_user_data(email: str, **kwargs) -> bool:
    """Update user profile data (GDPR Art. 16 - Right to rectification).
    Allowed fields: name."""
    allowed_fields = {"name"}
    keys = _load_keys()
    for key_hash, user_data in keys.items():
        if user_data.get("email") == email:
            for field, value in kwargs.items():
                if field in allowed_fields:
                    keys[key_hash][field] = value
            _save_keys(keys)
            return True
    return False


def delete_api_key_by_email(email: str) -> bool:
    """Delete API key for a user by email. Returns True if deleted."""
    keys = _load_keys()
    to_delete = [k for k, v in keys.items() if v.get("email") == email]
    if not to_delete:
        return False
    for key_hash in to_delete:
        del keys[key_hash]
    _save_keys(keys)
    return True


def verify_user_email(email: str, code: str) -> bool:
    """Verify a user's email with the 6-digit code. Returns True if verified."""
    keys = _load_keys()
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    for key_hash, user_data in keys.items():
        if user_data.get("email") == email:
            if user_data.get("email_verified"):
                return True  # Already verified

            # Check expiration
            expires = user_data.get("verification_expires", "")
            if expires and datetime.fromisoformat(expires) < datetime.utcnow():
                return False  # Code expired

            # Check code
            if user_data.get("verification_code") == code_hash:
                keys[key_hash]["email_verified"] = True
                keys[key_hash].pop("verification_code", None)
                keys[key_hash].pop("verification_expires", None)
                _save_keys(keys)
                return True

            return False  # Wrong code

    return False  # User not found


def regenerate_verification_code(email: str) -> str | None:
    """Regenerate a verification code for a user. Returns the new raw code or None."""
    keys = _load_keys()

    for key_hash, user_data in keys.items():
        if user_data.get("email") == email:
            if user_data.get("email_verified"):
                return None  # Already verified

            new_code = f"{secrets.randbelow(900000) + 100000}"
            keys[key_hash]["verification_code"] = hashlib.sha256(new_code.encode()).hexdigest()
            keys[key_hash]["verification_expires"] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
            _save_keys(keys)
            return new_code

    return None


def is_admin(user: dict) -> bool:
    """Check if user has admin privileges. Explicitly separate from tier - business tier does NOT grant admin."""
    return user.get("is_admin", False) is True


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

    # Ensure is_admin is always an explicit boolean (never truthy string/int)
    user["is_admin"] = user.get("is_admin", False) is True

    return user


async def get_current_verified_user(api_key: str = Security(api_key_header)) -> dict:
    """Dependency to get current authenticated user with verified email"""
    user = await get_current_user(api_key)
    if not user.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please verify your email first via POST /api/v1/auth/verify-email",
        )
    return user


async def get_optional_user(api_key: str = Security(api_key_header)) -> dict | None:
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


def get_key_hash_for_user(user: dict) -> str | None:
    """Get the key hash for a user (needed for updates)"""
    keys = _load_keys()
    for key_hash, user_data in keys.items():
        if user_data.get("email") == user.get("email"):
            return key_hash
    return None


def generate_unsubscribe_token(email: str) -> str:
    """Generate an HMAC token for email unsubscribe links."""
    return hmac.new(_UNSUBSCRIBE_SECRET.encode(), email.encode(), hashlib.sha256).hexdigest()[:32]


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Verify an unsubscribe token is valid for the given email."""
    expected = generate_unsubscribe_token(email)
    return hmac.compare_digest(expected, token)


def disable_notifications_for_user(email: str) -> int:
    """Set notify_email to null for all watches owned by email. Returns count of watches updated."""
    from ..storage import get_db

    db = get_db()
    watches = db.get_watches_by_user(email)
    count = 0
    for w in watches:
        if w.get("notify_email"):
            db.update_watch(w["id"], notify_email=None)
            count += 1
    return count


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
