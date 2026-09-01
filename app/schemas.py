"""Pydantic v2 request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import BLOOD_GROUPS, OFFER_STATUS, REQUEST_STATUS, ROLES, URGENCY


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    role: str = Field(default="donor")
    city: str = Field(min_length=2, max_length=80)

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ROLES:
            raise ValueError("role must be one of donor, requester, admin")
        return v

    @field_validator("full_name", "city")
    @classmethod
    def strip_fields(cls, v: str) -> str:
        return v.strip()


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ---------- Users / Donors ----------
class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str
    role: str
    city: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DonorProfileIn(BaseModel):
    blood_group: str
    last_donation_date: datetime | None = None
    is_available: bool = True
    medical_notes: str = Field(default="", max_length=1000)

    @field_validator("blood_group")
    @classmethod
    def valid_blood(cls, v: str) -> str:
        if v not in BLOOD_GROUPS:
            raise ValueError(f"blood_group must be one of {BLOOD_GROUPS}")
        return v


class DonorOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: str
    city: str
    blood_group: str
    is_available: bool
    eligible: bool
    donation_count: int
    last_donation_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DonorUpdateIn(BaseModel):
    is_available: bool | None = None
    last_donation_date: datetime | None = None
    medical_notes: str | None = Field(default=None, max_length=1000)


# ---------- Requests ----------
class BloodRequestIn(BaseModel):
    patient_name: str = Field(min_length=2, max_length=120)
    blood_group: str
    units: int = Field(default=1, ge=1, le=20)
    city: str = Field(min_length=2, max_length=80)
    hospital: str | None = Field(default=None, max_length=160)
    urgency: str = Field(default="normal")
    note: str = Field(default="", max_length=2000)

    @field_validator("blood_group")
    @classmethod
    def valid_blood(cls, v: str) -> str:
        if v not in BLOOD_GROUPS:
            raise ValueError(f"blood_group must be one of {BLOOD_GROUPS}")
        return v

    @field_validator("urgency")
    @classmethod
    def valid_urgency(cls, v: str) -> str:
        if v not in URGENCY:
            raise ValueError("urgency must be one of normal, urgent, emergency")
        return v

    @field_validator("patient_name", "city")
    @classmethod
    def strip_fields(cls, v: str) -> str:
        return v.strip()


class BloodRequestOut(BaseModel):
    id: int
    request_number: str
    patient_name: str
    blood_group: str
    units: int
    city: str
    hospital: str | None
    urgency: str
    status: str
    note: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    offer_count: int = 0

    model_config = {"from_attributes": True}


# ---------- Offers ----------
class OfferIn(BaseModel):
    message: str = Field(default="", max_length=1000)


class OfferOut(BaseModel):
    id: int
    request_id: int
    donor_id: int
    donor_name: str = ""
    blood_group: str = ""
    status: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Stats ----------
class StatsOut(BaseModel):
    total_donors: int
    eligible_donors: int
    open_requests: int
    fulfilled_requests: int
    total_requests: int
    requests_by_blood_group: dict[str, int]
    donors_by_blood_group: dict[str, int]


TokenOut.model_rebuild()
