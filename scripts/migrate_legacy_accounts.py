#!/usr/bin/env python3
"""Migration: add missing security fields to legacy accounts.

Some early accounts were created before email verification and GDPR fields
were added. This script backfills defaults for those accounts.

Usage:
    python3 scripts/migrate_legacy_accounts.py
"""
import json
import os
import shutil

DATA_DIR = "/opt/claude-ceo/workspace/arkwatch/data"
BACKUP_DIR = f"{DATA_DIR}/.backup_pre_field_migration"
API_KEYS_FILE = f"{DATA_DIR}/api_keys.json"

# Fields that should exist on every account with their default values
REQUIRED_FIELDS = {
    "is_admin": False,
    "email_verified": False,
    "privacy_accepted": False,
    "privacy_accepted_at": None,
    "privacy_accepted_ip": None,
    "stripe_customer_id": None,
    "stripe_subscription_id": None,
    "subscription_status": None,
}


def main():
    if not os.path.exists(API_KEYS_FILE):
        print("api_keys.json not found, nothing to migrate.")
        return

    with open(API_KEYS_FILE, "r") as f:
        keys = json.load(f)

    # Backup first
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, "api_keys.json")
    shutil.copy2(API_KEYS_FILE, dest)
    print(f"Backed up: {API_KEYS_FILE} -> {dest}")

    migrated = 0
    for key_hash, user_data in keys.items():
        fields_added = []
        for field, default_val in REQUIRED_FIELDS.items():
            if field not in user_data:
                user_data[field] = default_val
                fields_added.append(field)
        if fields_added:
            migrated += 1
            short_hash = key_hash[:12] + "..."
            print(f"  Account {short_hash}: added {len(fields_added)} fields: {', '.join(fields_added)}")

    if migrated == 0:
        print("All accounts already have required fields. Nothing to migrate.")
        return

    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2, default=str)

    print(f"\nDone! Migrated {migrated} account(s).")


if __name__ == "__main__":
    main()
