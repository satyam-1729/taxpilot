from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
    employer_name: str | None
    employee_pan: str | None
    gross_salary: Decimal | None
    total_tds: Decimal | None
    taxable_income: Decimal | None
    tax_payable: Decimal | None
    regime: str | None
    parsed_json: dict[str, Any] | None
    error: str | None
    created_at: datetime
    parsed_at: datetime | None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    id: UUID
    status: str
    deduplicated: bool = Field(..., description="True if this exact file was already parsed for this user")
