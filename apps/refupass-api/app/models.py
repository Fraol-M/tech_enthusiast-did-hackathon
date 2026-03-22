from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)


class Household(TimestampMixin, Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    family_size: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    settlement: Mapped[str] = mapped_column(String(120), nullable=False)

    beneficiaries: Mapped[list["Beneficiary"]] = relationship(back_populates="household")


class Beneficiary(TimestampMixin, Base):
    __tablename__ = "beneficiaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beneficiary_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    auth_subject: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    program_name: Mapped[str] = mapped_column(String(120), nullable=False)
    distribution_site: Mapped[str] = mapped_column(String(120), nullable=False)
    ration_tier: Mapped[str] = mapped_column(String(60), nullable=False)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), nullable=False)

    household: Mapped[Household] = relationship(back_populates="beneficiaries")
    eligibility_records: Mapped[list["Eligibility"]] = relationship(back_populates="beneficiary")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="beneficiary")
    grievances: Mapped[list["Grievance"]] = relationship(back_populates="beneficiary")
    issuance_sessions: Mapped[list["IssuanceSession"]] = relationship(back_populates="beneficiary")


class AidCycle(TimestampMixin, Base):
    __tablename__ = "aid_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    eligibility_records: Mapped[list["Eligibility"]] = relationship(back_populates="aid_cycle")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="aid_cycle")
    grievances: Mapped[list["Grievance"]] = relationship(back_populates="aid_cycle")
    issuance_sessions: Mapped[list["IssuanceSession"]] = relationship(back_populates="aid_cycle")


class Eligibility(TimestampMixin, Base):
    __tablename__ = "eligibility"
    __table_args__ = (UniqueConstraint("beneficiary_id", "aid_cycle_id", name="uq_eligibility_beneficiary_cycle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("beneficiaries.id"), nullable=False)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    beneficiary: Mapped[Beneficiary] = relationship(back_populates="eligibility_records")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="eligibility_records")


class Redemption(TimestampMixin, Base):
    __tablename__ = "redemptions"
    __table_args__ = (UniqueConstraint("beneficiary_id", "aid_cycle_id", name="uq_redemption_beneficiary_cycle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("beneficiaries.id"), nullable=False)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    worker_username: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_reference: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="delivered")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    beneficiary: Mapped[Beneficiary] = relationship(back_populates="redemptions")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="redemptions")


class Grievance(TimestampMixin, Base):
    __tablename__ = "grievances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("beneficiaries.id"), nullable=False)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    redemption_id: Mapped[int | None] = mapped_column(ForeignKey("redemptions.id"), nullable=True)

    beneficiary: Mapped[Beneficiary] = relationship(back_populates="grievances")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="grievances")


class IssuanceSession(TimestampMixin, Base):
    __tablename__ = "issuance_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("beneficiaries.id"), nullable=False)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    issuer_id: Mapped[str] = mapped_column(String(80), nullable=False)
    credential_configuration_id: Mapped[str] = mapped_column(String(120), nullable=False)
    launch_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="created")
    qr_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    beneficiary: Mapped[Beneficiary] = relationship(back_populates="issuance_sessions")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="issuance_sessions")
