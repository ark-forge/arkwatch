"""PII encryption module for RGPD Art. 32 compliance.

Encrypts personal data (emails, names) at rest using Fernet (AES-128-CBC + HMAC).
The encryption key is derived from ARKWATCH_PII_KEY environment variable.
If the key is not set, encryption is a no-op (graceful degradation for migration).
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

_PII_KEY_ENV = "ARKWATCH_PII_KEY"
_ENC_PREFIX = "enc:"
_fernet_cache = None
_warned = False

logger = logging.getLogger(__name__)


def _get_fernet():
    """Get Fernet instance from environment key. Returns None if key not configured."""
    global _fernet_cache, _warned
    if _fernet_cache is not None:
        return _fernet_cache

    raw_key = os.getenv(_PII_KEY_ENV)
    if not raw_key:
        if not _warned:
            logger.warning(
                f"RGPD: {_PII_KEY_ENV} not set — PII encryption disabled. "
                "Set this variable to enable encryption at rest."
            )
            _warned = True
        return None

    try:
        _fernet_cache = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
    except Exception:
        derived = hashlib.sha256(raw_key.encode()).digest()
        _fernet_cache = Fernet(base64.urlsafe_b64encode(derived))
    return _fernet_cache


def encrypt_pii(value: str) -> str:
    """Encrypt a PII string. Returns 'enc:<base64>' format.
    If key not configured, already encrypted, or empty, returns as-is."""
    if not value or value.startswith(_ENC_PREFIX):
        return value
    f = _get_fernet()
    if f is None:
        return value
    encrypted = f.encrypt(value.encode())
    return _ENC_PREFIX + encrypted.decode()


def decrypt_pii(value: str) -> str:
    """Decrypt a PII string. If not encrypted (no 'enc:' prefix), returns as-is."""
    if not value or not value.startswith(_ENC_PREFIX):
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        decrypted = f.decrypt(value[len(_ENC_PREFIX) :].encode())
        return decrypted.decode()
    except InvalidToken:
        return value


def is_encrypted(value: str) -> bool:
    """Check if a value is already encrypted."""
    return bool(value and value.startswith(_ENC_PREFIX))


def mask_email(email: str) -> str:
    """Mask an email for safe logging: apps.desiorac@gmail.com -> a***c@g***.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    parts = domain.split(".")
    masked_local = local[0] + "***" + local[-1] if len(local) > 1 else "***"
    masked_domain = parts[0][0] + "***" if parts[0] else "***"
    return f"{masked_local}@{masked_domain}.{parts[-1]}" if len(parts) > 1 else f"{masked_local}@{masked_domain}"
