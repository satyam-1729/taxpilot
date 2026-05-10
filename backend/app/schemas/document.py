from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.crypto import read_decimal, read_json, read_str

if TYPE_CHECKING:
    from app.models import Document


# ─────────────────────────────────────────────────────────────────────────────
# Form 16 extracted shape
# ─────────────────────────────────────────────────────────────────────────────

class Form16Employer(BaseModel):
    name: str | None = None
    tan: str | None = None
    address: str | None = None


class Form16Employee(BaseModel):
    name: str | None = None
    pan: str | None = None


class Form16TDSQuarter(BaseModel):
    quarter: int = Field(..., description="1, 2, 3, or 4")
    amount_paid: Decimal | None = None
    tds_deducted: Decimal | None = None
    challan_no: str | None = None
    date: str | None = None


class Form16TDS(BaseModel):
    quarters: list[Form16TDSQuarter] = Field(default_factory=list)
    total_tds: Decimal | None = None


class Form16LineItem(BaseModel):
    section: str | None = Field(None, description="IT Act section, e.g. '80C', '10(13A)', '16(ia)'")
    label: str
    amount: Decimal


class Form16Salary(BaseModel):
    gross: Decimal | None = None
    components: list[Form16LineItem] = Field(default_factory=list)
    section_10_exemptions: list[Form16LineItem] = Field(default_factory=list)
    section_16: list[Form16LineItem] = Field(default_factory=list)


class Form16Data(BaseModel):
    """Versioned schema for parsed Form 16 data. Bump parser_version when this changes."""

    schema_version: int = 1
    ay: str | None = None
    fy: str | None = None
    regime: str | None = Field(None, description="'old' or 'new'")
    employer: Form16Employer = Field(default_factory=Form16Employer)
    employee: Form16Employee = Field(default_factory=Form16Employee)
    tds: Form16TDS = Field(default_factory=Form16TDS)
    salary: Form16Salary = Field(default_factory=Form16Salary)
    chapter_vi_a: list[Form16LineItem] = Field(default_factory=list)
    taxable_income: Decimal | None = None
    tax_payable: Decimal | None = None


# ─────────────────────────────────────────────────────────────────────────────
# AIS / TIS extracted shape
#
# The Annual Information Statement (and its sister Taxpayer Information
# Summary) is the IT Dept's consolidated ledger of every reported transaction
# against a PAN. The schema below captures the *aggregates* the tax engine
# needs and a normalized breakdown of the source-level entries the
# reconciler will compare against Form 16 / bank / broker docs.
# ─────────────────────────────────────────────────────────────────────────────

class AisTaxpayer(BaseModel):
    name: str | None = None
    pan: str | None = None
    aadhaar_last4: str | None = None


class AisTdsEntry(BaseModel):
    """One row from Part B (TDS/TCS) — what a deductor reported against this PAN."""

    deductor_name: str | None = None
    deductor_tan: str | None = None
    section: str | None = Field(None, description="TDS section, e.g. '192' (salary), '194A' (interest)")
    amount_paid: Decimal | None = None
    tds_deducted: Decimal | None = None


class AisInterestEntry(BaseModel):
    """SFT-016 (savings/FD interest) — one bank/payer per row."""

    payer_name: str | None = None
    account_last4: str | None = None
    section: str | None = None
    amount: Decimal


class AisDividendEntry(BaseModel):
    payer_name: str | None = None
    isin: str | None = None
    amount: Decimal


class AisCapitalGains(BaseModel):
    """Capital-gains aggregates as reported in AIS (cross-checked against broker P&L)."""

    stcg_111a: Decimal | None = None
    stcg_non_equity: Decimal | None = None
    ltcg_112a: Decimal | None = None
    ltcg_non_equity: Decimal | None = None


class AisOtherIncome(BaseModel):
    label: str
    section: str | None = None
    amount: Decimal


class AisData(BaseModel):
    """Versioned schema for parsed AIS / Form 26AS / TIS data."""

    schema_version: int = 1
    source: str | None = Field(None, description="'ais', 'tis', or '26as'")
    ay: str | None = None
    fy: str | None = None
    taxpayer: AisTaxpayer = Field(default_factory=AisTaxpayer)

    tds_entries: list[AisTdsEntry] = Field(default_factory=list)
    total_tds: Decimal | None = None
    salary_total: Decimal | None = Field(
        None, description="Sum of section-192 amounts paid (cross-check against Form 16 gross)."
    )

    interest_income: list[AisInterestEntry] = Field(default_factory=list)
    interest_total: Decimal | None = None

    dividends: list[AisDividendEntry] = Field(default_factory=list)
    dividends_total: Decimal | None = None

    capital_gains: AisCapitalGains = Field(default_factory=AisCapitalGains)

    other_income: list[AisOtherIncome] = Field(default_factory=list)
    exempt_income_total: Decimal | None = None

    advance_tax_paid: Decimal | None = None
    self_assessment_tax_paid: Decimal | None = None
    refunds_received: Decimal | None = None

    total_income_reported: Decimal | None = Field(
        None, description="TIS taxpayer-summary total income (only present in TIS variant)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# API I/O
# ─────────────────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    """List/detail response for a document row."""

    id: UUID
    doc_type: str
    status: str
    file_name: str
    file_size_bytes: int
    ay: str | None
    fy: str | None = None
    # Form 16 fields
    employer_name: str | None
    employee_pan: str | None
    gross_salary: Decimal | None
    total_tds: Decimal | None
    taxable_income: Decimal | None
    tax_payable: Decimal | None
    regime: str | None
    # Capital gains fields
    broker: str | None = None
    stcg_111a: Decimal | None = None
    stcg_non_equity: Decimal | None = None
    ltcg_112a: Decimal | None = None
    ltcg_non_equity: Decimal | None = None
    dividends_total: Decimal | None = None
    exempt_income_total: Decimal | None = None
    total_invested: Decimal | None = None
    # Common
    parsed_json: dict[str, Any] | None
    error: str | None
    created_at: datetime
    parsed_at: datetime | None

    class Config:
        from_attributes = True


def document_out_from(row: "Document", dek: bytes | None) -> "DocumentOut":
    """Build a DocumentOut, decrypting PII / financial fields with the user's DEK."""
    return DocumentOut(
        id=row.id,
        doc_type=row.doc_type,
        status=row.status,
        file_name=row.file_name,
        file_size_bytes=row.file_size_bytes,
        ay=row.ay,
        fy=row.fy,
        # Form 16 PII / financials
        employer_name=read_str(row.employer_name_ct, dek),
        employee_pan=read_str(row.employee_pan_ct, dek),
        gross_salary=read_decimal(row.gross_salary_ct, dek),
        total_tds=read_decimal(row.total_tds_ct, dek),
        taxable_income=read_decimal(row.taxable_income_ct, dek),
        tax_payable=read_decimal(row.tax_payable_ct, dek),
        regime=row.regime,
        # Capital gains
        broker=row.broker,
        stcg_111a=read_decimal(row.stcg_111a_ct, dek),
        stcg_non_equity=read_decimal(row.stcg_non_equity_ct, dek),
        ltcg_112a=read_decimal(row.ltcg_112a_ct, dek),
        ltcg_non_equity=read_decimal(row.ltcg_non_equity_ct, dek),
        dividends_total=read_decimal(row.dividends_total_ct, dek),
        exempt_income_total=read_decimal(row.exempt_income_total_ct, dek),
        total_invested=read_decimal(row.total_invested_ct, dek),
        # Common
        parsed_json=read_json(row.parsed_json_ct, dek),
        error=row.error,
        created_at=row.created_at,
        parsed_at=row.parsed_at,
    )


class UploadResponse(BaseModel):
    id: UUID
    status: str
    deduplicated: bool = Field(..., description="True if this exact file was already parsed for this user")
