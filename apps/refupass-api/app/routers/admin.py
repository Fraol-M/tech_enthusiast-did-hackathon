from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import runtime
from ..database import get_db
from ..domain.operations import (
    create_or_reuse_program_enrollment,
    get_current_cycle_record,
    get_current_eligibility_for_enrollment,
    get_issuance_session_for_ngo_or_404,
    get_or_create_entitlement,
    get_or_create_program,
    get_person_or_404,
    get_program_enrollment_for_ngo_or_404,
)
from ..domain.serializers import (
    serialize_issuance_session,
    serialize_person,
    serialize_program,
    serialize_program_enrollment,
    serialize_program_enrollment_detail,
    serialize_staff_user,
)
from ..models import Eligibility, Household, IssuanceSession, Person, Program, ProgramEnrollment, User
from ..schemas import (
    AidCycleResponse,
    AidWorkerCreate,
    EligibilitySnapshot,
    EligibilityUpdate,
    IssuanceSessionRequest,
    IssuanceSessionResponse,
    IssuanceSessionStatusUpdate,
    PersonSummary,
    PrintablePass,
    ProgramSummary,
    ProgramEnrollmentCreate,
    ProgramEnrollmentDetail,
    ProgramEnrollmentSummary,
    StaffUserResponse,
)
from ..security import require_role
from ..services.issuance import build_issuance_payload, build_printable_pass


router = APIRouter()


@router.get("/aid-cycles/current", response_model=AidCycleResponse)
def get_current_cycle(
    _user: User = Depends(require_role("ngo_admin", "aid_worker")),
    db: Session = Depends(get_db),
) -> AidCycleResponse:
    return AidCycleResponse.model_validate(get_current_cycle_record(db))


@router.get("/aid-workers", response_model=list[StaffUserResponse])
def list_aid_workers(
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> list[StaffUserResponse]:
    workers = db.scalars(
        select(User)
        .options(joinedload(User.ngo))
        .where(User.ngo_id == user.ngo_id, User.role == "aid_worker")
        .order_by(User.display_name.asc())
    ).all()
    return [serialize_staff_user(worker) for worker in workers]


@router.post("/aid-workers", response_model=StaffUserResponse, status_code=status.HTTP_201_CREATED)
def create_aid_worker(
    payload: AidWorkerCreate,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> StaffUserResponse:
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing:
        raise HTTPException(status_code=400, detail="Username is already in use")

    aid_worker = User(
        username=payload.username,
        password=payload.password,
        role="aid_worker",
        display_name=payload.display_name,
        ngo_id=user.ngo_id,
    )
    db.add(aid_worker)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create aid worker") from exc
    db.refresh(aid_worker)
    aid_worker = db.scalar(select(User).options(joinedload(User.ngo)).where(User.id == aid_worker.id))
    return serialize_staff_user(aid_worker)


@router.get("/people", response_model=list[PersonSummary])
def list_people(
    search: str | None = None,
    _user: User = Depends(require_role("platform_admin", "ngo_admin")),
    db: Session = Depends(get_db),
) -> list[PersonSummary]:
    query = (
        select(Person)
        .outerjoin(Household, Household.id == Person.household_id)
        .options(joinedload(Person.household))
    )
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                Household.settlement.ilike(pattern),
                Household.household_code.ilike(pattern),
                Person.full_name.ilike(pattern),
                Person.auth_subject.ilike(pattern),
                Person.person_code.ilike(pattern),
            )
        ).order_by(
            case((Household.settlement.ilike(pattern), 0), (Person.full_name.ilike(pattern), 1), else_=2),
            Person.full_name.asc(),
        )
    else:
        query = query.order_by(Person.full_name.asc())
    people = db.scalars(query).all()
    return [serialize_person(person) for person in people]


@router.get("/programs", response_model=list[ProgramSummary])
def list_programs(
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> list[ProgramSummary]:
    programs = db.scalars(
        select(Program)
        .options(joinedload(Program.ngo))
        .where(Program.ngo_id == user.ngo_id, Program.is_active.is_(True))
        .order_by(Program.name.asc())
    ).all()
    return [serialize_program(program) for program in programs]


@router.get("/program-enrollments", response_model=list[ProgramEnrollmentSummary])
def list_program_enrollments(
    search: str | None = None,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> list[ProgramEnrollmentSummary]:
    aid_cycle = get_current_cycle_record(db)
    query = (
        select(ProgramEnrollment)
        .join(Program, Program.id == ProgramEnrollment.program_id)
        .join(Person, Person.id == ProgramEnrollment.person_id)
        .options(
            joinedload(ProgramEnrollment.person).joinedload(Person.household),
            joinedload(ProgramEnrollment.program).joinedload(Program.ngo),
        )
        .where(Program.ngo_id == user.ngo_id)
        .order_by(ProgramEnrollment.created_at.desc())
    )
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                Person.full_name.ilike(pattern),
                Person.auth_subject.ilike(pattern),
                Person.person_code.ilike(pattern),
                ProgramEnrollment.enrollment_code.ilike(pattern),
                Program.name.ilike(pattern),
            )
        )
    enrollments = db.scalars(query).all()
    return [serialize_program_enrollment(db, enrollment, aid_cycle) for enrollment in enrollments]


@router.post("/program-enrollments", response_model=ProgramEnrollmentSummary, status_code=status.HTTP_201_CREATED)
def create_program_enrollment(
    payload: ProgramEnrollmentCreate,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> ProgramEnrollmentSummary:
    person = get_person_or_404(db, payload.person_id)
    if payload.program_id:
        program = db.scalar(
            select(Program)
            .options(joinedload(Program.ngo))
            .where(Program.id == payload.program_id, Program.ngo_id == user.ngo_id)
        )
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")
    else:
        if not payload.program_name:
            raise HTTPException(status_code=400, detail="Program name is required when no existing program is selected")
        program = get_or_create_program(
            db,
            ngo_id=user.ngo_id,
            name=payload.program_name,
            assistance_type=payload.assistance_type,
            distribution_site=payload.distribution_site,
            ration_tier=payload.ration_tier,
        )

    distribution_site = payload.distribution_site or program.default_distribution_site
    ration_tier = payload.ration_tier or program.default_ration_tier
    if not distribution_site or not ration_tier:
        raise HTTPException(
            status_code=400,
            detail="Distribution site and ration tier are required before enrollment can be created",
        )
    enrollment = create_or_reuse_program_enrollment(
        db,
        person=person,
        program=program,
        distribution_site=distribution_site,
        ration_tier=ration_tier,
        created_by_user_id=user.id,
        notes=payload.notes,
    )
    db.commit()
    enrollment = get_program_enrollment_for_ngo_or_404(db, enrollment.id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    return serialize_program_enrollment(db, enrollment, aid_cycle)


@router.get("/program-enrollments/{enrollment_id}", response_model=ProgramEnrollmentDetail)
def get_program_enrollment(
    enrollment_id: int,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> ProgramEnrollmentDetail:
    enrollment = get_program_enrollment_for_ngo_or_404(db, enrollment_id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    return serialize_program_enrollment_detail(db, enrollment, aid_cycle)


@router.patch("/program-enrollments/{enrollment_id}/eligibility", response_model=EligibilitySnapshot)
def update_program_enrollment_eligibility(
    enrollment_id: int,
    payload: EligibilityUpdate,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> EligibilitySnapshot:
    enrollment = get_program_enrollment_for_ngo_or_404(db, enrollment_id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    if not eligibility:
        eligibility = Eligibility(
            program_enrollment_id=enrollment.id,
            aid_cycle_id=aid_cycle.id,
            status=payload.status,
            notes=payload.notes,
            valid_from=payload.valid_from or aid_cycle.starts_on,
            valid_until=payload.valid_until or aid_cycle.ends_on,
        )
        db.add(eligibility)
    else:
        eligibility.status = payload.status
        eligibility.notes = payload.notes
        eligibility.valid_from = payload.valid_from or eligibility.valid_from
        eligibility.valid_until = payload.valid_until or eligibility.valid_until

    db.commit()
    db.refresh(eligibility)
    return EligibilitySnapshot.model_validate(eligibility)


@router.post("/issuance-sessions", response_model=IssuanceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_issuance_session(
    payload: IssuanceSessionRequest,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> IssuanceSessionResponse:
    enrollment = get_program_enrollment_for_ngo_or_404(db, payload.program_enrollment_id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    if not eligibility or eligibility.status != "eligible":
        raise HTTPException(status_code=400, detail="Enrollment is not eligible for the current cycle")

    session_token, session_payload = build_issuance_payload(enrollment, eligibility, aid_cycle, runtime.settings)
    get_or_create_entitlement(
        db,
        enrollment=enrollment,
        aid_cycle=aid_cycle,
        issuer_id=session_payload["issuer_id"],
        credential_configuration_id=session_payload["credential_configuration_id"],
    )
    session = IssuanceSession(
        program_enrollment_id=enrollment.id,
        aid_cycle_id=aid_cycle.id,
        session_token=session_token,
        issuer_id=session_payload["issuer_id"],
        credential_configuration_id=session_payload["credential_configuration_id"],
        launch_url=session_payload["launch_url"],
        status=session_payload["status"],
        qr_payload=session_payload["qr_payload"],
    )
    db.add(session)
    db.commit()
    session = db.scalar(
        select(IssuanceSession)
        .options(
            joinedload(IssuanceSession.program_enrollment)
            .joinedload(ProgramEnrollment.person)
            .joinedload(Person.household),
            joinedload(IssuanceSession.program_enrollment)
            .joinedload(ProgramEnrollment.program)
            .joinedload(Program.ngo),
            joinedload(IssuanceSession.aid_cycle),
        )
        .where(IssuanceSession.session_token == session_token)
    )
    return serialize_issuance_session(db, session, session.program_enrollment, aid_cycle)


@router.get("/issuance-sessions/{session_token}", response_model=IssuanceSessionResponse)
def get_issuance_session(
    session_token: str,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> IssuanceSessionResponse:
    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    aid_cycle = issuance_session.aid_cycle or get_current_cycle_record(db)
    return serialize_issuance_session(db, issuance_session, enrollment, aid_cycle)


@router.get("/issuance-sessions/{session_token}/pass", response_model=PrintablePass)
def get_issuance_session_pass(
    session_token: str,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> PrintablePass:
    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    aid_cycle = issuance_session.aid_cycle or get_current_cycle_record(db)
    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    if not eligibility:
        raise HTTPException(status_code=400, detail="Enrollment does not have an eligibility record for this cycle")
    return build_printable_pass(
        enrollment,
        eligibility,
        aid_cycle,
        pass_id=issuance_session.session_token,
    )


@router.patch("/issuance-sessions/{session_token}/status", response_model=IssuanceSessionResponse)
def update_issuance_session_status(
    session_token: str,
    payload: IssuanceSessionStatusUpdate,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> IssuanceSessionResponse:
    allowed_statuses = {"pass_downloaded"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unsupported issuance session status")

    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    if issuance_session.status not in {"pass_ready", "pass_downloaded"}:
        raise HTTPException(status_code=400, detail="Issuance session can no longer be updated from the RefuPass pass flow")

    issuance_session.status = payload.status
    db.commit()
    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    aid_cycle = issuance_session.aid_cycle or get_current_cycle_record(db)
    return serialize_issuance_session(db, issuance_session, enrollment, aid_cycle)
