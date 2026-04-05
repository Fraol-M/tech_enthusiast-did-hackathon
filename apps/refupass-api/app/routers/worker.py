from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import runtime
from ..database import get_db
from ..domain.operations import (
    get_current_cycle_record,
    get_current_eligibility_for_enrollment,
    get_current_redemption_for_enrollment,
    get_or_create_entitlement,
    get_program_enrollment_for_ngo_or_404,
    update_latest_issuance_session_status,
)
from ..domain.serializers import serialize_grievance, serialize_redemption
from ..domain.verification import (
    build_lookup_payload,
    determine_business_status,
    find_enrollment_from_payload,
    parse_verification_payload,
)
from ..models import AidCycle, Grievance, Program, ProgramEnrollment, Redemption, User
from ..schemas import (
    GrievanceCreate,
    GrievanceResponse,
    RedeemRequest,
    RedemptionResponse,
    WorkerEnrollmentSummary,
    WorkerVerifyRequest,
    WorkerVerifyResponse,
)
from ..security import require_role
from ..services.pass_tokens import verify_pass_payload


router = APIRouter()


@router.post("/worker/verify", response_model=WorkerVerifyResponse)
async def worker_verify(
    payload: WorkerVerifyRequest,
    user: User = Depends(require_role("aid_worker")),
    db: Session = Depends(get_db),
) -> WorkerVerifyResponse:
    verification_payload, verification_mode = parse_verification_payload(payload)
    if verification_mode in {"credential_json", "credential_string"}:
        verification = await runtime.verify_client.verify(verification_payload)
    elif verification_mode == "refupass_pass_qr":
        signature_valid = verify_pass_payload(verification_payload, runtime.settings.pass_signing_secret)
        verification = {
            "cryptographicStatus": "valid" if signature_valid else "invalid",
            "details": {
                "mode": verification_mode,
                "signatureVerified": signature_valid,
                "passId": verification_payload.get("passId"),
            },
        }
    else:
        verification = {
            "cryptographicStatus": "not_checked",
            "details": {
                "mode": verification_mode,
                "warning": "Printable-pass fallback was used; cryptographic VC verification was not performed.",
            },
        }

    lookup_payload = build_lookup_payload(
        verification_payload,
        payload.credential_metadata,
        verification.get("details", {}).get("claims"),
    )
    enrollment = find_enrollment_from_payload(db, lookup_payload, payload.program_enrollment_id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id) if enrollment else None
    redemption = get_current_redemption_for_enrollment(db, enrollment.id, aid_cycle.id) if enrollment else None
    business_status, can_redeem = determine_business_status(
        verification["cryptographicStatus"],
        enrollment,
        eligibility,
        redemption,
        lookup_payload,
        allow_business_only=verification_mode == "printable_pass_qr",
    )

    issuance_status_updated = False
    if (
        enrollment
        and aid_cycle
        and verification["cryptographicStatus"] == "valid"
        and verification_mode in {"credential_json", "credential_string", "refupass_pass_qr"}
    ):
        issuance_status_updated = update_latest_issuance_session_status(
            db,
            program_enrollment_id=enrollment.id,
            aid_cycle_id=aid_cycle.id,
            status_value="credential_verified",
        )
        if issuance_status_updated:
            db.commit()

    enrollment_summary = None
    if enrollment:
        enrollment_summary = WorkerEnrollmentSummary(
            record_id=enrollment.id,
            enrollment_code=enrollment.enrollment_code,
            person_code=enrollment.person.person_code,
            subject_id=enrollment.person.person_code,
            household_id=enrollment.person.household.household_code if enrollment.person.household else "",
            full_name=enrollment.person.full_name,
            family_size=enrollment.person.household.family_size if enrollment.person.household else 0,
            program_name=enrollment.program.name,
            ration_tier=enrollment.ration_tier,
        )

    return WorkerVerifyResponse(
        verification_mode=verification_mode,
        cryptographic_status=verification["cryptographicStatus"],
        business_status=business_status,
        enrollment_summary=enrollment_summary,
        aid_cycle=aid_cycle.name if enrollment else None,
        distribution_site=enrollment.distribution_site if enrollment else None,
        can_redeem=can_redeem,
        verification_reference=str(uuid4()),
        details={
            **verification.get("details", {}),
            "verificationMode": verification_mode,
            "verifiedBy": user.display_name,
            "ngoName": user.ngo.name,
            "lookupPayload": lookup_payload,
            "eligibilityStatus": eligibility.status if eligibility else None,
            "redemptionStatus": redemption.delivery_status if redemption else None,
            "issuanceSessionUpdated": issuance_status_updated,
        },
    )


@router.post("/worker/redeem", response_model=RedemptionResponse, status_code=status.HTTP_201_CREATED)
def worker_redeem(
    payload: RedeemRequest,
    user: User = Depends(require_role("aid_worker")),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    enrollment = get_program_enrollment_for_ngo_or_404(db, payload.program_enrollment_id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    existing = get_current_redemption_for_enrollment(db, enrollment.id, aid_cycle.id)
    if existing:
        raise HTTPException(status_code=400, detail="Current cycle already redeemed")

    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    if not eligibility or eligibility.status != "eligible":
        raise HTTPException(status_code=400, detail="Enrollment is not eligible for redemption")

    entitlement = get_or_create_entitlement(
        db,
        enrollment=enrollment,
        aid_cycle=aid_cycle,
        issuer_id="RefuPass",
        credential_configuration_id="RefuPassPrintablePass",
    )
    redemption = Redemption(
        program_enrollment_id=enrollment.id,
        entitlement_id=entitlement.id,
        aid_cycle_id=aid_cycle.id,
        worker_username=user.username,
        verification_reference=payload.verification_reference,
        delivery_status="delivered",
        notes=payload.notes,
    )
    db.add(redemption)
    update_latest_issuance_session_status(
        db,
        program_enrollment_id=enrollment.id,
        aid_cycle_id=aid_cycle.id,
        status_value="redeemed",
    )
    db.commit()
    db.refresh(redemption)
    return RedemptionResponse.model_validate(redemption)


@router.get("/redemptions", response_model=list[RedemptionResponse])
def list_redemptions(
    user: User = Depends(require_role("ngo_admin", "aid_worker")),
    db: Session = Depends(get_db),
) -> list[RedemptionResponse]:
    redemptions = db.scalars(
        select(Redemption)
        .join(ProgramEnrollment, ProgramEnrollment.id == Redemption.program_enrollment_id)
        .join(Program, Program.id == ProgramEnrollment.program_id)
        .where(Program.ngo_id == user.ngo_id)
        .order_by(Redemption.created_at.desc())
    ).all()
    return [serialize_redemption(redemption) for redemption in redemptions]


@router.post("/grievances", response_model=GrievanceResponse, status_code=status.HTTP_201_CREATED)
def create_grievance(
    payload: GrievanceCreate,
    user: User = Depends(require_role("aid_worker")),
    db: Session = Depends(get_db),
) -> GrievanceResponse:
    enrollment = get_program_enrollment_for_ngo_or_404(db, payload.program_enrollment_id, user.ngo_id)
    aid_cycle = db.get(AidCycle, payload.aid_cycle_id) if payload.aid_cycle_id else get_current_cycle_record(db)

    grievance = Grievance(
        person_id=enrollment.person_id,
        program_enrollment_id=enrollment.id,
        aid_cycle_id=aid_cycle.id,
        created_by=user.username,
        reason=payload.reason,
        details=payload.details,
        status="open",
        redemption_id=payload.redemption_id,
    )
    db.add(grievance)
    db.commit()
    db.refresh(grievance)
    return GrievanceResponse.model_validate(grievance)


@router.get("/grievances", response_model=list[GrievanceResponse])
def list_grievances(
    user: User = Depends(require_role("ngo_admin", "aid_worker")),
    db: Session = Depends(get_db),
) -> list[GrievanceResponse]:
    grievances = db.scalars(
        select(Grievance)
        .join(ProgramEnrollment, ProgramEnrollment.id == Grievance.program_enrollment_id)
        .join(Program, Program.id == ProgramEnrollment.program_id)
        .where(Program.ngo_id == user.ngo_id)
        .order_by(Grievance.created_at.desc())
    ).all()
    return [serialize_grievance(grievance) for grievance in grievances]
