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
    ngo_id: Mapped[int | None] = mapped_column(ForeignKey("ngos.id"), nullable=True, index=True)

    ngo: Mapped["Ngo | None"] = relationship(back_populates="users")


class Ngo(TimestampMixin, Base):
    __tablename__ = "ngos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)

    users: Mapped[list["User"]] = relationship(back_populates="ngo")
    programs: Mapped[list["Program"]] = relationship(back_populates="ngo")


class Household(TimestampMixin, Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    family_size: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    settlement: Mapped[str] = mapped_column(String(120), nullable=False)

    people: Mapped[list["Person"]] = relationship(back_populates="household")


class Person(TimestampMixin, Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    auth_subject: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    identity_status: Mapped[str] = mapped_column(String(30), nullable=False, default="record_only", index=True)
    identity_provider: Mapped[str | None] = mapped_column(String(60), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id"), nullable=True)

    household: Mapped[Household | None] = relationship(back_populates="people")
    enrollments: Mapped[list["ProgramEnrollment"]] = relationship(back_populates="person")
    grievances: Mapped[list["Grievance"]] = relationship(back_populates="person")
    identity_verification_sessions: Mapped[list["IdentityVerificationSession"]] = relationship(back_populates="person")


class Program(TimestampMixin, Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("ngo_id", "name", name="uq_program_ngo_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ngo_id: Mapped[int] = mapped_column(ForeignKey("ngos.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    assistance_type: Mapped[str] = mapped_column(String(40), nullable=False, default="food")
    default_distribution_site: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_ration_tier: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    ngo: Mapped[Ngo] = relationship(back_populates="programs")
    enrollments: Mapped[list["ProgramEnrollment"]] = relationship(back_populates="program")


class ProgramEnrollment(TimestampMixin, Base):
    __tablename__ = "program_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False, index=True)
    enrollment_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    distribution_site: Mapped[str] = mapped_column(String(120), nullable=False)
    ration_tier: Mapped[str] = mapped_column(String(60), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped[Person] = relationship(back_populates="enrollments")
    program: Mapped[Program] = relationship(back_populates="enrollments")
    created_by_user: Mapped[User | None] = relationship()
    eligibility_records: Mapped[list["Eligibility"]] = relationship(back_populates="program_enrollment")
    entitlements: Mapped[list["Entitlement"]] = relationship(back_populates="program_enrollment")
    issuance_sessions: Mapped[list["IssuanceSession"]] = relationship(back_populates="program_enrollment")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="program_enrollment")
    grievances: Mapped[list["Grievance"]] = relationship(back_populates="program_enrollment")


class AidCycle(TimestampMixin, Base):
    __tablename__ = "aid_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    eligibility_records: Mapped[list["Eligibility"]] = relationship(back_populates="aid_cycle")
    entitlements: Mapped[list["Entitlement"]] = relationship(back_populates="aid_cycle")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="aid_cycle")
    grievances: Mapped[list["Grievance"]] = relationship(back_populates="aid_cycle")
    issuance_sessions: Mapped[list["IssuanceSession"]] = relationship(back_populates="aid_cycle")


class Eligibility(TimestampMixin, Base):
    __tablename__ = "eligibility"
    __table_args__ = (UniqueConstraint("program_enrollment_id", "aid_cycle_id", name="uq_eligibility_enrollment_cycle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_enrollment_id: Mapped[int] = mapped_column(ForeignKey("program_enrollments.id"), nullable=False, index=True)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    program_enrollment: Mapped[ProgramEnrollment] = relationship(back_populates="eligibility_records")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="eligibility_records")


class Entitlement(TimestampMixin, Base):
    __tablename__ = "entitlements"
    __table_args__ = (UniqueConstraint("program_enrollment_id", "aid_cycle_id", name="uq_entitlement_enrollment_cycle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_enrollment_id: Mapped[int] = mapped_column(ForeignKey("program_enrollments.id"), nullable=False)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    entitlement_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    credential_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    issuer_id: Mapped[str] = mapped_column(String(80), nullable=False)
    credential_configuration_id: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="issued", index=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    program_enrollment: Mapped[ProgramEnrollment] = relationship(back_populates="entitlements")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="entitlements")
    redemptions: Mapped[list["Redemption"]] = relationship(back_populates="entitlement")


class Redemption(TimestampMixin, Base):
    __tablename__ = "redemptions"
    __table_args__ = (
        UniqueConstraint("program_enrollment_id", "aid_cycle_id", name="uq_redemption_enrollment_cycle"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_enrollment_id: Mapped[int] = mapped_column(ForeignKey("program_enrollments.id"), nullable=False, index=True)
    entitlement_id: Mapped[int] = mapped_column(ForeignKey("entitlements.id"), nullable=False, index=True)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    worker_username: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_reference: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="delivered")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    program_enrollment: Mapped[ProgramEnrollment] = relationship(back_populates="redemptions")
    entitlement: Mapped[Entitlement] = relationship(back_populates="redemptions")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="redemptions")


class Grievance(TimestampMixin, Base):
    __tablename__ = "grievances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), nullable=False, index=True)
    program_enrollment_id: Mapped[int] = mapped_column(ForeignKey("program_enrollments.id"), nullable=False, index=True)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    redemption_id: Mapped[int | None] = mapped_column(ForeignKey("redemptions.id"), nullable=True)

    person: Mapped[Person] = relationship(back_populates="grievances")
    program_enrollment: Mapped[ProgramEnrollment] = relationship(back_populates="grievances")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="grievances")


class IssuanceSession(TimestampMixin, Base):
    __tablename__ = "issuance_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_enrollment_id: Mapped[int] = mapped_column(ForeignKey("program_enrollments.id"), nullable=False, index=True)
    aid_cycle_id: Mapped[int] = mapped_column(ForeignKey("aid_cycles.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    issuer_id: Mapped[str] = mapped_column(String(80), nullable=False)
    credential_configuration_id: Mapped[str] = mapped_column(String(120), nullable=False)
    launch_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="created")
    qr_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    program_enrollment: Mapped[ProgramEnrollment] = relationship(back_populates="issuance_sessions")
    aid_cycle: Mapped[AidCycle] = relationship(back_populates="issuance_sessions")


class IdentityVerificationSession(TimestampMixin, Base):
    __tablename__ = "identity_verification_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="esignet")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    state: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    nonce: Mapped[str] = mapped_column(String(120), nullable=False)
    client_id: Mapped[str] = mapped_column(String(120), nullable=False)
    code_verifier: Mapped[str] = mapped_column(String(255), nullable=False)
    private_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    authorize_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    person_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    verified_subject: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True, index=True)

    person: Mapped[Person | None] = relationship(back_populates="identity_verification_sessions")
