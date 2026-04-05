from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import (
    AidCycle,
    Eligibility,
    Entitlement,
    Household,
    IssuanceSession,
    Person,
    Program,
    ProgramEnrollment,
    Redemption,
)


def generate_reference(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def get_or_create_program(
    db: Session,
    *,
    ngo_id: int,
    name: str,
    assistance_type: str = "food",
    distribution_site: str | None = None,
    ration_tier: str | None = None,
) -> Program:
    program = db.scalar(select(Program).where(Program.ngo_id == ngo_id, Program.name == name))
    if program:
        if distribution_site and not program.default_distribution_site:
            program.default_distribution_site = distribution_site
        if ration_tier and not program.default_ration_tier:
            program.default_ration_tier = ration_tier
        return program

    program = Program(
        ngo_id=ngo_id,
        name=name,
        assistance_type=assistance_type,
        default_distribution_site=distribution_site,
        default_ration_tier=ration_tier,
        is_active=True,
    )
    db.add(program)
    db.flush()
    return program


def create_household_from_payload(
    db: Session,
    *,
    household_code: str,
    family_size: int,
    primary_contact_name: str,
    settlement: str,
) -> Household:
    household = db.scalar(select(Household).where(Household.household_code == household_code))
    if household:
        return household

    household = Household(
        household_code=household_code,
        family_size=family_size,
        primary_contact_name=primary_contact_name,
        settlement=settlement,
    )
    db.add(household)
    db.flush()
    return household


def create_or_reuse_person(
    db: Session,
    *,
    person_code: str | None,
    auth_subject: str | None,
    full_name: str,
    phone: str | None,
    gender: str | None,
    identity_status: str,
    identity_provider: str | None,
    verified_at: datetime | None,
    household: Household | None,
) -> Person:
    person = None
    if auth_subject:
        person = db.scalar(select(Person).where(Person.auth_subject == auth_subject))
    if person_code and not person:
        person = db.scalar(select(Person).where(Person.person_code == person_code))

    if person:
        if household and person.household_id is None:
            person.household = household
        if not person.phone and phone:
            person.phone = phone
        if not person.gender and gender:
            person.gender = gender
        if identity_provider and not person.identity_provider:
            person.identity_provider = identity_provider
        if verified_at and person.verified_at is None:
            person.verified_at = verified_at
        return person

    person = Person(
        person_code=person_code or generate_reference("PER"),
        auth_subject=auth_subject,
        full_name=full_name,
        phone=phone,
        gender=gender,
        identity_status=identity_status,
        identity_provider=identity_provider,
        verified_at=verified_at,
        household=household,
    )
    db.add(person)
    db.flush()
    return person


def create_or_reuse_program_enrollment(
    db: Session,
    *,
    person: Person,
    program: Program,
    distribution_site: str,
    ration_tier: str,
    created_by_user_id: int | None,
    notes: str | None,
) -> ProgramEnrollment:
    enrollment = db.scalar(
        select(ProgramEnrollment).where(
            ProgramEnrollment.person_id == person.id,
            ProgramEnrollment.program_id == program.id,
            ProgramEnrollment.status.in_(("active", "pending")),
        )
    )
    if enrollment:
        if not enrollment.distribution_site and distribution_site:
            enrollment.distribution_site = distribution_site
        if not enrollment.ration_tier and ration_tier:
            enrollment.ration_tier = ration_tier
        return enrollment

    enrollment = ProgramEnrollment(
        person_id=person.id,
        program_id=program.id,
        enrollment_code=generate_reference("ENR"),
        status="active",
        distribution_site=distribution_site,
        ration_tier=ration_tier,
        created_by_user_id=created_by_user_id,
        notes=notes,
    )
    db.add(enrollment)
    db.flush()
    return enrollment


def get_or_create_entitlement(
    db: Session,
    *,
    enrollment: ProgramEnrollment,
    aid_cycle: AidCycle,
    issuer_id: str,
    credential_configuration_id: str,
    credential_id: str | None = None,
) -> Entitlement:
    entitlement = db.scalar(
        select(Entitlement).where(
            Entitlement.program_enrollment_id == enrollment.id,
            Entitlement.aid_cycle_id == aid_cycle.id,
        )
    )
    if entitlement:
        if credential_id and not entitlement.credential_id:
            entitlement.credential_id = credential_id
        return entitlement

    entitlement = Entitlement(
        program_enrollment_id=enrollment.id,
        aid_cycle_id=aid_cycle.id,
        entitlement_code=generate_reference("ENT"),
        credential_id=credential_id,
        issuer_id=issuer_id,
        credential_configuration_id=credential_configuration_id,
        status="issued",
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.combine(aid_cycle.ends_on, time.max),
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def get_current_cycle_record(db: Session) -> AidCycle:
    cycle = db.scalar(select(AidCycle).where(AidCycle.is_current.is_(True)))
    if cycle:
        return cycle
    cycle = db.scalar(select(AidCycle).order_by(AidCycle.starts_on.desc()))
    if not cycle:
        raise HTTPException(status_code=500, detail="No aid cycle configured")
    return cycle


def get_current_eligibility_for_enrollment(db: Session, enrollment_id: int, aid_cycle_id: int) -> Eligibility | None:
    return db.scalar(
        select(Eligibility).where(
            Eligibility.program_enrollment_id == enrollment_id,
            Eligibility.aid_cycle_id == aid_cycle_id,
        )
    )


def get_current_redemption_for_enrollment(db: Session, enrollment_id: int, aid_cycle_id: int) -> Redemption | None:
    return db.scalar(
        select(Redemption).where(
            Redemption.program_enrollment_id == enrollment_id,
            Redemption.aid_cycle_id == aid_cycle_id,
        )
    )


def get_person_or_404(db: Session, person_id: int) -> Person:
    person = db.scalar(select(Person).options(joinedload(Person.household)).where(Person.id == person_id))
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


def get_program_enrollment_for_ngo_or_404(db: Session, enrollment_id: int, ngo_id: int) -> ProgramEnrollment:
    enrollment = db.scalar(
        select(ProgramEnrollment)
        .join(Program, Program.id == ProgramEnrollment.program_id)
        .options(
            joinedload(ProgramEnrollment.person).joinedload(Person.household),
            joinedload(ProgramEnrollment.program).joinedload(Program.ngo),
        )
        .where(ProgramEnrollment.id == enrollment_id, Program.ngo_id == ngo_id)
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Program enrollment not found")
    return enrollment


def get_issuance_session_for_ngo_or_404(db: Session, session_token: str, ngo_id: int) -> tuple[IssuanceSession, ProgramEnrollment]:
    issuance_session = db.scalar(
        select(IssuanceSession)
        .join(ProgramEnrollment, ProgramEnrollment.id == IssuanceSession.program_enrollment_id)
        .join(Program, Program.id == ProgramEnrollment.program_id)
        .options(
            joinedload(IssuanceSession.program_enrollment)
            .joinedload(ProgramEnrollment.person)
            .joinedload(Person.household),
            joinedload(IssuanceSession.program_enrollment)
            .joinedload(ProgramEnrollment.program)
            .joinedload(Program.ngo),
            joinedload(IssuanceSession.aid_cycle),
        )
        .where(IssuanceSession.session_token == session_token, Program.ngo_id == ngo_id)
    )
    if not issuance_session:
        raise HTTPException(status_code=404, detail="Issuance session not found")
    return issuance_session, issuance_session.program_enrollment


def update_latest_issuance_session_status(
    db: Session,
    *,
    program_enrollment_id: int,
    aid_cycle_id: int,
    status_value: str,
) -> bool:
    issuance_session = db.scalar(
        select(IssuanceSession)
        .where(
            IssuanceSession.program_enrollment_id == program_enrollment_id,
            IssuanceSession.aid_cycle_id == aid_cycle_id,
        )
        .order_by(IssuanceSession.created_at.desc())
    )
    terminal_statuses = {"redeemed"}
    if not issuance_session or issuance_session.status == status_value or issuance_session.status in terminal_statuses:
        return False
    issuance_session.status = status_value
    return True
