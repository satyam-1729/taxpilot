from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CHAR, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Document(Base):
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

    ay: Mapped[str | None] = mapped_column(String(16))
    fy: Mapped[str | None] = mapped_column(String(16))
    employer_name: Mapped[str | None] = mapped_column(String(256))
    employer_tan: Mapped[str | None] = mapped_column(String(32))
    employee_pan: Mapped[str | None] = mapped_column(String(16))
    gross_salary: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_tds: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    taxable_income: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    tax_payable: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    regime: Mapped[str | None] = mapped_column(String(8))

    # Capital gains denormalized fields (doc_type='capital_gains')
    broker: Mapped[str | None] = mapped_column(String(64))
    stcg_111a: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    stcg_non_equity: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ltcg_112a: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ltcg_non_equity: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    dividends_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    exempt_income_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_invested: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    parsed_json: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[dict | None] = mapped_column(JSONB)

    # ── Envelope-encrypted mirrors (added 0007) ──────────────────────────────
    # Populated by the dual-write path during the rollout. Once backfilled,
    # the plaintext columns above will be dropped.
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
