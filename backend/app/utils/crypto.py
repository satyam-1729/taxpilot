import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    """Derive a Fernet key from the configured field_encryption_key."""
    raw = get_settings().field_encryption_key.encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    # Fernet expects url-safe base64-encoded 32-byte key
    import base64

    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_field(value: str) -> bytes:
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt_field(value: bytes) -> str:
    try:
        return _fernet().decrypt(value).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Could not decrypt field") from e
