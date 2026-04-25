import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_REGEX = re.compile(r"^\d{12}$")


class SessionRequest(BaseModel):
    id_token: str = Field(..., description="Firebase ID token from the web SDK")


class SessionResponse(BaseModel):
    token: str
    user: "UserOut"


class UserOut(BaseModel):
    id: UUID
    phone: str | None
    email: str | None
    name: str | None
    verified: bool
    verified_at: datetime | None

    class Config:
        from_attributes = True


class KycRequest(BaseModel):
    pan: str = Field(..., description="10-character PAN, e.g. ABCDE1234F")
    aadhaar: str = Field(..., description="12-digit Aadhaar number, no spaces")

    @field_validator("pan")
    @classmethod
    def _pan_format(cls, v: str) -> str:
        v = v.strip().upper()
        if not PAN_REGEX.match(v):
            raise ValueError("PAN must match AAAAA9999A")
        return v

    @field_validator("aadhaar")
    @classmethod
    def _aadhaar_format(cls, v: str) -> str:
        v = re.sub(r"\s+", "", v)
        if not AADHAAR_REGEX.match(v):
            raise ValueError("Aadhaar must be 12 digits")
        return v


SessionResponse.model_rebuild()
