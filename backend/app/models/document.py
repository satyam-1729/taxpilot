from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CHAR, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
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

    parsed_json: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[dict | None] = mapped_column(JSONB)
    parser_provider: Mapped[str | None] = mapped_column(String(32))
    parser_model: Mapped[str | None] = mapped_column(String(64))
    parser_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
