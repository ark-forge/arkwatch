#!/usr/bin/env python3
"""Key rotation: decrypt PII with old key, re-encrypt with new key.

Usage:
    ARKWATCH_PII_KEY_OLD=<old_key> ARKWATCH_PII_KEY=<new_key> python3 scripts/rotate_pii_key.py

This script:
1. Backs up data files
2. Decrypts PII fields using old key
3. Re-encrypts PII fields using new key
4. Verifies all decryption works with new key
"""
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.crypto import _ENC_PREFIX, is_encrypted

from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
BACKUP_DIR = f"{DATA_DIR}/.backup_pre_rotation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

API_KEYS_FILE = f"{DATA_DIR}/api_keys.json"
WATCHES_FILE = f"{DATA_DIR}/watches.json"

API_KEY_PII_FIELDS = ("email", "name", "privacy_accepted_ip")
WATCH_PII_FIELDS = ("notify_email", "user_email")


def make_fernet(raw_key: str) -> Fernet:
    """Create Fernet instance from a raw key string."""
    try:
        return Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
    except Exception:
        derived = hashlib.sha256(raw_key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(derived))


def decrypt_value(f_old: Fernet, value: str) -> str:
    """Decrypt a single enc: prefixed value."""
    if not value or not value.startswith(_ENC_PREFIX):
        return value
    try:
        return f_old.decrypt(value[len(_ENC_PREFIX):].encode()).decode()
    except InvalidToken:
        print(f"  WARNING: Could not decrypt value (already rotated or corrupt?)")
        return value


def encrypt_value(f_new: Fernet, value: str) -> str:
    """Encrypt a plaintext value with new key."""
    if not value or value.startswith(_ENC_PREFIX):
        return value
    return _ENC_PREFIX + f_new.encrypt(value.encode()).decode()


def backup_file(filepath):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, os.path.basename(filepath))
    shutil.copy2(filepath, dest)
    os.chmod(dest, 0o600)
    print(f"  Backed up: {filepath} -> {dest}")


def rotate_api_keys(f_old: Fernet, f_new: Fernet) -> int:
    if not os.path.exists(API_KEYS_FILE):
        print("  api_keys.json not found, skipping")
        return 0

    backup_file(API_KEYS_FILE)

    with open(API_KEYS_FILE, "r") as f:
        keys = json.load(f)

    count = 0
    for key_hash, user_data in keys.items():
        for field in API_KEY_PII_FIELDS:
            val = user_data.get(field)
            if val and isinstance(val, str) and is_encrypted(val):
                plaintext = decrypt_value(f_old, val)
                if not is_encrypted(plaintext):
                    user_data[field] = encrypt_value(f_new, plaintext)
                    count += 1

    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2, default=str)
    os.chmod(API_KEYS_FILE, 0o600)

    print(f"  Re-encrypted {count} PII fields in api_keys.json")
    return count


def rotate_watches(f_old: Fernet, f_new: Fernet) -> int:
    if not os.path.exists(WATCHES_FILE):
        print("  watches.json not found, skipping")
        return 0

    backup_file(WATCHES_FILE)

    with open(WATCHES_FILE, "r") as f:
        watches = json.load(f)

    count = 0
    for watch in watches:
        for field in WATCH_PII_FIELDS:
            val = watch.get(field)
            if val and isinstance(val, str) and is_encrypted(val):
                plaintext = decrypt_value(f_old, val)
                if not is_encrypted(plaintext):
                    watch[field] = encrypt_value(f_new, plaintext)
                    count += 1

    with open(WATCHES_FILE, "w") as f:
        json.dump(watches, f, indent=2, default=str)
    os.chmod(WATCHES_FILE, 0o600)

    print(f"  Re-encrypted {count} PII fields in watches.json")
    return count


def verify(f_new: Fernet):
    """Verify all encrypted data can be decrypted with new key."""
    print("\nVerification with new key:")
    errors = 0

    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r") as f:
            keys = json.load(f)
        for key_hash, user_data in keys.items():
            for field in API_KEY_PII_FIELDS:
                val = user_data.get(field)
                if val and is_encrypted(val):
                    try:
                        decrypted = f_new.decrypt(val[len(_ENC_PREFIX):].encode()).decode()
                        assert not is_encrypted(decrypted)
                    except (InvalidToken, AssertionError):
                        print(f"  FAIL: {field} in {key_hash[:8]}...")
                        errors += 1

    if os.path.exists(WATCHES_FILE):
        with open(WATCHES_FILE, "r") as f:
            watches = json.load(f)
        for i, watch in enumerate(watches):
            for field in WATCH_PII_FIELDS:
                val = watch.get(field)
                if val and is_encrypted(val):
                    try:
                        decrypted = f_new.decrypt(val[len(_ENC_PREFIX):].encode()).decode()
                        assert not is_encrypted(decrypted)
                    except (InvalidToken, AssertionError):
                        print(f"  FAIL: {field} in watch #{i}")
                        errors += 1

    if errors == 0:
        print("  All verifications passed!")
    else:
        print(f"  {errors} verification(s) FAILED!")
    return errors


def main():
    old_key = os.getenv("ARKWATCH_PII_KEY_OLD")
    new_key = os.getenv("ARKWATCH_PII_KEY")

    if not old_key:
        print("ERROR: ARKWATCH_PII_KEY_OLD environment variable not set (current key)")
        sys.exit(1)
    if not new_key:
        print("ERROR: ARKWATCH_PII_KEY environment variable not set (new key)")
        sys.exit(1)
    if old_key == new_key:
        print("ERROR: Old and new keys are identical. Nothing to rotate.")
        sys.exit(1)

    f_old = make_fernet(old_key)
    f_new = make_fernet(new_key)

    print("=== ArkWatch PII Key Rotation ===\n")
    print(f"Backup directory: {BACKUP_DIR}\n")

    print("Step 1: Re-encrypting api_keys.json...")
    n1 = rotate_api_keys(f_old, f_new)

    print("\nStep 2: Re-encrypting watches.json...")
    n2 = rotate_watches(f_old, f_new)

    if n1 + n2 > 0:
        errors = verify(f_new)
        if errors > 0:
            print("\n!!! ROTATION FAILED - Restoring from backup !!!")
            for fname in ["api_keys.json", "watches.json"]:
                backup = os.path.join(BACKUP_DIR, fname)
                target = os.path.join(DATA_DIR, fname)
                if os.path.exists(backup):
                    shutil.copy2(backup, target)
                    os.chmod(target, 0o600)
                    print(f"  Restored: {target}")
            print("Rotation rolled back. Old key still active.")
            sys.exit(1)
    else:
        print("\nNo encrypted PII found to rotate.")

    print(f"\nDone! Total fields re-encrypted: {n1 + n2}")
    print(f"Backups saved to: {BACKUP_DIR}")
    print("\nNext steps:")
    print("  1. Update /opt/claude-ceo/credentials/.env with the new key")
    print("  2. Restart services: sudo systemctl restart arkwatch-api arkwatch-worker")
    print("  3. Verify health: curl http://127.0.0.1:8080/health")


if __name__ == "__main__":
    main()
