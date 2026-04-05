from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AidCycle, Grievance, IdentityVerificationSession, Person, ProgramEnrollment, Redemption
from ..schemas import (
    GrievanceResponse,
    IdentityVerificationSessionStatus,
    IssuanceSessionResponse,
    PersonDetail,
    PersonSummary,
    PlatformNgoSummary,
    ProgramSummary,
    ProgramEnrollmentDetail,
    ProgramEnrollmentSummary,
    RedemptionResponse,
    StaffUserResponse,
)
from ..services.issuance import build_credential_preview, build_issuance_instructions, build_printable_pass
from .operations import get_current_eligibility_for_enrollment, get_current_redemption_for_enrollment, get_person_or_404


def serialize_person(person: Person) -> PersonSummary:
    return PersonSummary.model_validate(
        {
            **person.__dict__,
            "household": person.household,
        }
    )


def serialize_person_detail(db: Session, person: Person) -> PersonDetail:
    enrollment_count = db.scalar(select(func.count()).select_from(ProgramEnrollment).where(ProgramEnrollment.person_id == person.id))
    return PersonDetail.model_validate(
        {
            **serialize_person(person).model_dump(),
            "enrollment_count": enrollment_count or 0,
        }
    )


def serialize_program(program) -> ProgramSummary:
    return ProgramSummary.model_validate(
        {
            **program.__dict__,
            "ngo": program.ngo,
        }
    )


def serialize_program_enrollment(
    db: Session,
    enrollment: ProgramEnrollment,
    aid_cycle: AidCycle,
) -> ProgramEnrollmentSummary:
    current_eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    current_redemption = get_current_redemption_for_enrollment(db, enrollment.id, aid_cycle.id)
    return ProgramEnrollmentSummary.model_validate(
        {
            **enrollment.__dict__,
            "person": enrollment.person,
            "program": {
                **enrollment.program.__dict__,
                "ngo": enrollment.program.ngo,
            },
            "current_eligibility": current_eligibility,
            "current_redemption": current_redemption,
        }
    )


def serialize_redemption(redemption: Redemption) -> RedemptionResponse:
    return RedemptionResponse.model_validate(redemption)


def serialize_grievance(grievance: Grievance) -> GrievanceResponse:
    return GrievanceResponse.model_validate(grievance)


def serialize_staff_user(user) -> StaffUserResponse:
    return StaffUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        ngo_name=user.ngo.name if user.ngo else "RefuPass Platform",
    )


def serialize_platform_ngo(ngo) -> PlatformNgoSummary:
    ngo_admin = next((user for user in ngo.users if user.role == "ngo_admin"), None)
    aid_worker_count = sum(1 for user in ngo.users if user.role == "aid_worker")
    program_count = len(ngo.programs)
    enrollment_count = sum(len(program.enrollments) for program in ngo.programs)
    return PlatformNgoSummary(
        id=ngo.id,
        name=ngo.name,
        admin_display_name=ngo_admin.display_name if ngo_admin else None,
        admin_username=ngo_admin.username if ngo_admin else None,
        aid_worker_count=aid_worker_count,
        program_count=program_count,
        enrollment_count=enrollment_count,
    )


def serialize_identity_verification_session(
    db: Session,
    verification_session: IdentityVerificationSession,
) -> IdentityVerificationSessionStatus:
    person = get_person_or_404(db, verification_session.person_id) if verification_session.person_id else None
    return IdentityVerificationSessionStatus(
        session_token=verification_session.session_token,
        status=verification_session.status,
        provider=verification_session.provider,
        verified_subject=verification_session.verified_subject,
        error_message=verification_session.error_message,
        person=serialize_person_detail(db, person) if person else None,
    )


def serialize_issuance_session(
    db: Session,
    issuance_session,
    enrollment: ProgramEnrollment,
    aid_cycle: AidCycle,
) -> IssuanceSessionResponse:
    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    if not eligibility:
        raise HTTPException(status_code=400, detail="Enrollment does not have an eligibility record for this cycle")
    printable_pass = build_printable_pass(
        enrollment,
        eligibility,
        aid_cycle,
        pass_id=issuance_session.session_token,
    )

    return IssuanceSessionResponse(
        session_token=issuance_session.session_token,
        issuer_id=issuance_session.issuer_id,
        credential_configuration_id=issuance_session.credential_configuration_id,
        status=issuance_session.status,
        flow_type="refupass_native_pass",
        instructions=build_issuance_instructions(),
        credential_preview=build_credential_preview(enrollment, eligibility, aid_cycle),
        pass_id=printable_pass.pass_id,
        printable_pass=printable_pass,
        pass_download_url=f"/issuance-sessions/{issuance_session.session_token}/pass",
        external_wallet_flow=None,
    )


def serialize_program_enrollment_detail(
    db: Session,
    enrollment: ProgramEnrollment,
    aid_cycle: AidCycle,
) -> ProgramEnrollmentDetail:
    redemptions = db.scalars(
        select(Redemption)
        .where(Redemption.program_enrollment_id == enrollment.id)
        .order_by(Redemption.created_at.desc())
    ).all()
    grievances = db.scalars(
        select(Grievance)
        .where(Grievance.program_enrollment_id == enrollment.id)
        .order_by(Grievance.created_at.desc())
    ).all()
    summary = serialize_program_enrollment(db, enrollment, aid_cycle)
    return ProgramEnrollmentDetail.model_validate(
        {
            **summary.model_dump(),
            "redemptions": redemptions,
            "grievances": grievances,
        }
    )
