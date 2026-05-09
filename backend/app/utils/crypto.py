"""Envelope encryption (KEK→DEK) for PII at rest.

Two keys:
  KEK — master key in the server env (Settings.field_encryption_key).
        Single value app-wide. Versioned by 1-byte prefix for future rotation.
  DEK — random 32-byte key per user, stored *wrapped* on the user row.

Format on every ciphertext blob:
  [ 1 byte version ][ 12 byte nonce ][ ciphertext + 16 byte GCM tag ]

The version byte lets us rotate either key without a big-bang migration:
readers pick the right key by prefix, writers always use the current version.

Threat-model recap:
  - DB dump only          → ciphertext + wrapped DEKs, no KEK → unreadable.
  - App env only          → KEK but no ciphertext → unreadable.
  - DB + app env (full)   → readable. (Defense-in-depth limit.)
  - Stolen JWT (live)     → can read the user's own data via the API. The
                            auth check is the gate; the DEK is the lock.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import date
from decimal import Decimal
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


# ─────────────────────────────────────────────────────────────────────────────
# KEK — derived from the env-var master secret
# ─────────────────────────────────────────────────────────────────────────────
# Bumping this requires a re-wrap of every users.dek_wrapped row. See plan.
CURRENT_KEK_VERSION = 0x01

# The DEK ciphertext format version. Bump only on incompatible AEAD changes.
CURRENT_DEK_VERSION = 0x01


def _kek_bytes(version: int = CURRENT_KEK_VERSION) -> bytes:
    """Return the raw 32-byte KEK for the given version. SHA-256 of the env secret."""
    if version != CURRENT_KEK_VERSION:
        raise ValueError(f"Unsupported KEK version: {version}")
    raw = get_settings().field_encryption_key.encode("utf-8")
    return hashlib.sha256(raw).digest()


# ─────────────────────────────────────────────────────────────────────────────
# DEK — generation, wrap, unwrap
# ─────────────────────────────────────────────────────────────────────────────


def generate_dek() -> bytes:
    """Mint a fresh 32-byte (256-bit) DEK from a CSPRNG."""
    return secrets.token_bytes(32)


def wrap_dek(dek: bytes) -> bytes:
    """Encrypt the DEK with the current KEK. Result starts with the KEK version byte."""
    if len(dek) != 32:
        raise ValueError("DEK must be 32 bytes")
    aesgcm = AESGCM(_kek_bytes(CURRENT_KEK_VERSION))
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, dek, b"dek")  # AAD ties this blob to the DEK use
    return bytes([CURRENT_KEK_VERSION]) + nonce + ct


def unwrap_dek(wrapped: bytes) -> bytes:
    """Reverse of wrap_dek. Picks the KEK by version byte for forward-compat."""
    if not wrapped or len(wrapped) < 1 + 12 + 16:
        raise ValueError("wrapped DEK is too short")
    version = wrapped[0]
    nonce = wrapped[1:13]
    ct = wrapped[13:]
    aesgcm = AESGCM(_kek_bytes(version))
    try:
        return aesgcm.decrypt(nonce, ct, b"dek")
    except Exception as e:
        raise ValueError("Could not unwrap DEK — wrong key or tampered ciphertext") from e


# ─────────────────────────────────────────────────────────────────────────────
# Field-level: encrypt/decrypt with a per-user DEK
# ─────────────────────────────────────────────────────────────────────────────


def encrypt_with_dek(dek: bytes, plaintext: str | bytes) -> bytes:
    """AES-256-GCM encrypt under the DEK. Output is [version][nonce][ct||tag]."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    aesgcm = AESGCM(dek)
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return bytes([CURRENT_DEK_VERSION]) + nonce + ct


def decrypt_with_dek(dek: bytes, blob: bytes) -> bytes:
    """Reverse of encrypt_with_dek. Returns raw bytes — caller decodes."""
    if not blob or len(blob) < 1 + 12 + 16:
        raise ValueError("ciphertext is too short")
    version = blob[0]
    if version != CURRENT_DEK_VERSION:
        raise ValueError(f"Unsupported DEK ciphertext version: {version}")
    nonce = blob[1:13]
    ct = blob[13:]
    aesgcm = AESGCM(dek)
    try:
        return aesgcm.decrypt(nonce, ct, None)
    except Exception as e:
        raise ValueError("Could not decrypt field — wrong DEK or tampered ciphertext") from e


# ── Convenience wrappers for typed values ───────────────────────────────────

def encrypt_str(dek: bytes, value: str | None) -> bytes | None:
    return None if value is None else encrypt_with_dek(dek, value)


def decrypt_str(dek: bytes, blob: bytes | None) -> str | None:
    return None if blob is None else decrypt_with_dek(dek, blob).decode("utf-8")


def encrypt_decimal(dek: bytes, value: Decimal | None) -> bytes | None:
    return None if value is None else encrypt_with_dek(dek, str(value))


def decrypt_decimal(dek: bytes, blob: bytes | None) -> Decimal | None:
    return None if blob is None else Decimal(decrypt_with_dek(dek, blob).decode("utf-8"))


def encrypt_date(dek: bytes, value: date | None) -> bytes | None:
    return None if value is None else encrypt_with_dek(dek, value.isoformat())


def decrypt_date(dek: bytes, blob: bytes | None) -> date | None:
    return None if blob is None else date.fromisoformat(decrypt_with_dek(dek, blob).decode("utf-8"))


def encrypt_json(dek: bytes, obj: Any) -> bytes | None:
    if obj is None:
        return None
    payload = json.dumps(obj, separators=(",", ":"), default=str)
    return encrypt_with_dek(dek, payload)


def decrypt_json(dek: bytes, blob: bytes | None) -> Any:
    if blob is None:
        return None
    return json.loads(decrypt_with_dek(dek, blob).decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Blind indexes — deterministic HMAC for equality lookups on encrypted fields
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Read-with-fallback — used during Stage 3 cut-over.
# Prefer the ciphertext, fall back to plaintext if the row pre-dates backfill.
# After Stage 4 drops plaintext columns, the fallback is unreachable and these
# can shrink to plain `decrypt_*` calls.
# ─────────────────────────────────────────────────────────────────────────────


def read_str(ct: bytes | None, dek: bytes | None, *, fallback: str | None = None) -> str | None:
    if ct is not None and dek is not None:
        return decrypt_str(dek, ct)
    return fallback


def read_decimal(ct: bytes | None, dek: bytes | None, *, fallback: Decimal | None = None) -> Decimal | None:
    if ct is not None and dek is not None:
        return decrypt_decimal(dek, ct)
    return fallback


def read_date(ct: bytes | None, dek: bytes | None, *, fallback: date | None = None) -> date | None:
    if ct is not None and dek is not None:
        return decrypt_date(dek, ct)
    return fallback


def read_json(ct: bytes | None, dek: bytes | None, *, fallback: Any = None) -> Any:
    if ct is not None and dek is not None:
        return decrypt_json(dek, ct)
    return fallback


def blind_index(value: str | None) -> bytes | None:
    """HMAC-SHA256(KEK, normalized(value))[:16].

    Use for `WHERE email_bidx = ?` lookups when the email itself is encrypted.
    Same plaintext always yields the same index — so an attacker with the DB
    can correlate equal values, but cannot recover the plaintext without the
    KEK. 16 bytes give ~2^64 collision resistance which is fine for a UNIQUE
    or B-tree index.
    """
    if value is None:
        return None
    norm = value.strip().lower().encode("utf-8")
    if not norm:
        return None
    return hmac.new(_kek_bytes(), norm, hashlib.sha256).digest()[:16]
