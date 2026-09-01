"""SQLAlchemy ORM models."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ROLES = ["donor", "requester", "admin"]
URGENCY = ["normal", "urgent", "emergency"]
REQUEST_STATUS = ["open", "matched", "fulfilled", "cancelled", "expired"]
OFFER_STATUS = ["pending", "accepted", "declined", "withdrawn"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="donor")
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped["DonorProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class DonorProfile(Base):
    __tablename__ = "donor_profiles"
    __table_args__ = (Index("ix_donor_blood", "blood_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    blood_group: Mapped[str] = mapped_column(String(5), nullable=False)
    last_donation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    medical_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    donation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="profile")

    @property
    def eligible(self) -> bool:
        """Donor is eligible if available and hasn't donated in the last 56 days."""
        if not self.is_available:
            return False
        if self.last_donation_date is None:
            return True
        last = self.last_donation_date
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (utcnow() - last).days >= 56


class BloodRequest(Base):
    __tablename__ = "blood_requests"
    __table_args__ = (Index("ix_request_status_city_blood", "status", "city", "blood_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    patient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(5), nullable=False)
    units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    hospital: Mapped[str | None] = mapped_column(String(160), nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("request_id", "donor_id", name="uq_offer_request_donor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("blood_requests.id"), nullable=False)
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    request: Mapped[BloodRequest] = relationship(back_populates="offers")
