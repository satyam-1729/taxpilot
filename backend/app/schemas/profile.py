import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
ACCOUNT_NUMBER_REGEX = re.compile(r"^\d{6,18}$")


class BankAccountCreate(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=120)
    ifsc: str = Field(..., description="11-char IFSC, e.g. HDFC0001234")
    account_number: str = Field(..., description="6–18 digits")
    account_type: Literal["savings", "current"] = "savings"
    is_primary: bool = False

    @field_validator("ifsc")
    @classmethod
    def _ifsc_format(cls, v: str) -> str:
        v = v.strip().upper()
        if not IFSC_REGEX.match(v):
            raise ValueError("IFSC must be 4 letters + '0' + 6 alphanumeric (e.g. HDFC0001234)")
        return v

    @field_validator("account_number")
    @classmethod
    def _account_format(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not ACCOUNT_NUMBER_REGEX.match(v):
            raise ValueError("Account number must be 6–18 digits")
        return v

    @field_validator("bank_name")
    @classmethod
    def _bank_clean(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Bank name cannot be empty")
        return v


class BankAccountOut(BaseModel):
    id: UUID
    bank_name: str
    ifsc: str
    account_last4: str
    account_type: str
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True
