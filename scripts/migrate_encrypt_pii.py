#!/usr/bin/env python3
"""One-time migration: encrypt existing PII in JSON data files.

Usage:
    ARKWATCH_PII_KEY=<key> python3 scripts/migrate_encrypt_pii.py

This script:
1. Backs up existing data files
2. Encrypts PII fields (email, name, IP) in api_keys.json
3. Encrypts PII fields (notify_email, user_email) in watches.json
4. Verifies decryption works correctly
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.crypto import encrypt_pii, decrypt_pii, is_encrypted

DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
BACKUP_DIR = f"{DATA_DIR}/.backup_pre_encryption"

API_KEYS_FILE = f"{DATA_DIR}/api_keys.json"
WATCHES_FILE = f"{DATA_DIR}/watches.json"

API_KEY_PII_FIELDS = ("email", "name", "privacy_accepted_ip")
WATCH_PII_FIELDS = ("notify_email", "user_email")


def backup_file(filepath):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, os.path.basename(filepath))
    shutil.copy2(filepath, dest)
    print(f"  Backed up: {filepath} -> {dest}")


def migrate_api_keys():
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
            if val and isinstance(val, str) and not is_encrypted(val):
                user_data[field] = encrypt_pii(val)
                count += 1

    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2, default=str)

    print(f"  Encrypted {count} PII fields in api_keys.json")
    return count


def migrate_watches():
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
            if val and isinstance(val, str) and not is_encrypted(val):
                watch[field] = encrypt_pii(val)
                count += 1

    with open(WATCHES_FILE, "w") as f:
        json.dump(watches, f, indent=2, default=str)

    print(f"  Encrypted {count} PII fields in watches.json")
    return count


def verify():
    """Verify that encrypted data can be decrypted back."""
    print("\nVerification:")

    with open(API_KEYS_FILE, "r") as f:
        keys = json.load(f)
    for key_hash, user_data in keys.items():
        for field in API_KEY_PII_FIELDS:
            val = user_data.get(field)
            if val and is_encrypted(val):
                decrypted = decrypt_pii(val)
                assert not is_encrypted(decrypted), f"Failed to decrypt {field}"
                print(f"  OK: {field} decrypts correctly")

    with open(WATCHES_FILE, "r") as f:
        watches = json.load(f)
    for watch in watches:
        for field in WATCH_PII_FIELDS:
            val = watch.get(field)
            if val and is_encrypted(val):
                decrypted = decrypt_pii(val)
                assert not is_encrypted(decrypted), f"Failed to decrypt {field}"
                print(f"  OK: {field} decrypts correctly")

    print("  All verifications passed!")


def main():
    if not os.getenv("ARKWATCH_PII_KEY"):
        print("ERROR: ARKWATCH_PII_KEY environment variable not set")
        print("Generate: python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        sys.exit(1)

    print("=== ArkWatch PII Encryption Migration ===\n")
    print("Step 1: Encrypting api_keys.json...")
    n1 = migrate_api_keys()

    print("\nStep 2: Encrypting watches.json...")
    n2 = migrate_watches()

    if n1 + n2 > 0:
        verify()
    else:
        print("\nNo unencrypted PII found — already migrated or no data.")

    print(f"\nDone! Total fields encrypted: {n1 + n2}")
    print(f"Backups saved to: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
