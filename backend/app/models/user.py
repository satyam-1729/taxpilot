from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CHAR, Boolean, DateTime, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    """A taxpayer's account row.

    All PII (email, phone, name, dob, PAN, Aadhaar) is stored exclusively as
    AES-GCM ciphertext under a per-user DEK. The DEK itself is wrapped with
    the server KEK and lives in `dek_wrapped`. Lookup-by-email / lookup-by-
    phone uses the HMAC-SHA256 blind indexes (`email_bidx`, `phone_bidx`).
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    # Display-safe last-4s — useful in the UI without revealing the full PAN /
    # Aadhaar. Not considered PII on their own.
    pan_last4: Mapped[str | None] = mapped_column(CHAR(4))
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Envelope encryption ──────────────────────────────────────────────────
    # dek_wrapped: per-user 32-byte DEK encrypted with the server KEK. Always
    # populated for users created after migration 0007.
    # *_ct: AES-256-GCM ciphertext under the DEK.
    # *_bidx: HMAC-SHA256(KEK, lower(value))[:16] for equality lookups.
    dek_wrapped: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    email_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    email_bidx: Mapped[bytes | None] = mapped_column(LargeBinary, index=True)
    phone_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    phone_bidx: Mapped[bytes | None] = mapped_column(LargeBinary, index=True)
    name_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    dob_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    pan_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    aadhaar_ct: Mapped[bytes | None] = mapped_column(LargeBinary)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
