from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CHAR, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Document(Base):
    """A parsed tax document.

    All PII / financial fields (parsed_json, employer details, salary numbers,
    capital-gains numbers) live exclusively in the *_ct columns as AES-GCM
    ciphertext under the owning user's DEK. Filter / lookup columns
    (doc_type, status, ay, fy, regime, broker, sha256) stay plaintext because
    they are not PII and the dashboard pivots on them.
    """

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("user_id", "sha256", name="uq_documents_user_sha256"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", server_default="queued")

    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Filter/lookup metadata — non-PII, plaintext.
    ay: Mapped[str | None] = mapped_column(String(16))
    fy: Mapped[str | None] = mapped_column(String(16))
    regime: Mapped[str | None] = mapped_column(String(8))
    broker: Mapped[str | None] = mapped_column(String(64))

    # Confidence scores from the parser. Empty most of the time, never PII.
    confidence: Mapped[dict | None] = mapped_column(JSONB)

    # ── Envelope-encrypted PII / financials ─────────────────────────────────
    # AES-256-GCM ciphertext under the user's DEK. Decryption happens at the
    # API boundary in document_out_from(). Background workers unwrap the DEK
    # from the owning user row.
    parsed_json_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    employer_name_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    employer_tan_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    employee_pan_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    gross_salary_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    total_tds_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    taxable_income_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    tax_payable_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    stcg_111a_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    stcg_non_equity_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    ltcg_112a_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    ltcg_non_equity_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    dividends_total_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    exempt_income_total_ct: Mapped[bytes | None] = mapped_column(LargeBinary)
    total_invested_ct: Mapped[bytes | None] = mapped_column(LargeBinary)

    parser_provider: Mapped[str | None] = mapped_column(String(32))
    parser_model: Mapped[str | None] = mapped_column(String(64))
    parser_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
