from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CHAR, Boolean, Date, DateTime, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    dob: Mapped[date | None] = mapped_column(Date)

    pan_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    pan_last4: Mapped[str | None] = mapped_column(CHAR(4))
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Envelope encryption (added 0007) ─────────────────────────────────────
    # dek_wrapped is the per-user DEK encrypted with the server KEK. The
    # plaintext DEK lives only in process memory during a request. *_ct
    # columns are AES-GCM ciphertext under the DEK; *_bidx are HMAC blind
    # indexes on the KEK so we can still WHERE on encrypted fields.
    dek_wrapped: Mapped[bytes | None] = mapped_column(LargeBinary)
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
