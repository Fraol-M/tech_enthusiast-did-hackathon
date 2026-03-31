from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import func, inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import (
    AidCycle,
    Eligibility,
    Entitlement,
    Grievance,
    Household,
    IdentityVerificationSession,
    IssuanceSession,
    Ngo,
    Person,
    Program,
    ProgramEnrollment,
    Redemption,
    User,
)
from .schemas import (
    AdminRegisterRequest,
    AidCycleResponse,
    AidWorkerCreate,
    EligibilitySnapshot,
    EligibilityUpdate,
    GrievanceCreate,
    GrievanceResponse,
    HealthResponse,
    IdentityVerificationSessionResponse,
    IdentityVerificationSessionStatus,
    IdentityVerificationStartRequest,
    IssuanceSessionRequest,
    IssuanceSessionStatusUpdate,
    IssuanceSessionResponse,
    LoginRequest,
    LoginResponse,
    PersonDetail,
    PersonSummary,
    PlatformNgoSummary,
    ProgramEnrollmentCreate,
    ProgramEnrollmentDetail,
    ProgramEnrollmentSummary,
    RedeemRequest,
    RedemptionResponse,
    StaffUserResponse,
    WorkerEnrollmentSummary,
    WorkerVerifyRequest,
    WorkerVerifyResponse,
)
from .security import build_access_token, get_current_user, require_role
from .seed import seed_demo_data
from .services.esignet_verification import ESignetVerificationService
from .services.issuance import (
    build_credential_preview,
    build_external_wallet_flow,
    build_issuance_instructions,
    build_issuance_payload,
)
from .services.verify_client import InjiVerifyClient


settings = get_settings()
verify_client = InjiVerifyClient(settings)
esignet_service = ESignetVerificationService(settings)



def assert_supported_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    eligibility_columns = {column["name"] for column in inspector.get_columns("eligibility")} if "eligibility" in table_names else set()
    redemption_columns = {column["name"] for column in inspector.get_columns("redemptions")} if "redemptions" in table_names else set()
    grievance_columns = {column["name"] for column in inspector.get_columns("grievances")} if "grievances" in table_names else set()
    issuance_session_columns = (
        {column["name"] for column in inspector.get_columns("issuance_sessions")} if "issuance_sessions" in table_names else set()
    )




@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    assert_supported_schema()
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_reference(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


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


def serialize_redemption(redemption: Redemption) -> RedemptionResponse:
    return RedemptionResponse.model_validate(redemption)


def serialize_grievance(grievance: Grievance) -> GrievanceResponse:
    return GrievanceResponse.model_validate(grievance)


def serialize_staff_user(user: User) -> StaffUserResponse:
    return StaffUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        ngo_name=user.ngo.name if user.ngo else "RefuPass Platform",
    )


def serialize_platform_ngo(ngo: Ngo) -> PlatformNgoSummary:
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
    issuance_session: IssuanceSession,
    enrollment: ProgramEnrollment,
    aid_cycle: AidCycle,
) -> IssuanceSessionResponse:
    eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
    if not eligibility:
        raise HTTPException(status_code=400, detail="Enrollment does not have an eligibility record for this cycle")

    return IssuanceSessionResponse(
        session_token=issuance_session.session_token,
        issuer_id=issuance_session.issuer_id,
        credential_configuration_id=issuance_session.credential_configuration_id,
        status=issuance_session.status,
        flow_type="issuer_managed",
        instructions=build_issuance_instructions(),
        credential_preview=build_credential_preview(enrollment, eligibility, aid_cycle),
        external_wallet_flow=build_external_wallet_flow(settings),
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
    if not issuance_session or issuance_session.status == status_value:
        return False
    issuance_session.status = status_value
    return True


def is_verifiable_credential(payload: dict) -> bool:
    if payload.get("credentialSubject") or payload.get("proof"):
        return True
    credential_type = payload.get("type")
    if isinstance(credential_type, list):
        return "VerifiableCredential" in credential_type
    if isinstance(credential_type, str):
        return credential_type == "VerifiableCredential"
    return False


def parse_verification_payload(request: WorkerVerifyRequest) -> tuple[dict[str, Any] | str, str]:
    if request.credential:
        payload = request.credential
    elif request.credential_text:
        try:
            payload = json.loads(request.credential_text)
        except json.JSONDecodeError:
            payload = request.credential_text.strip()
            if not payload:
                raise HTTPException(status_code=400, detail="Credential text is empty")
    else:
        raise HTTPException(status_code=400, detail="Provide credential or credentialText")

    if isinstance(payload, str):
        return payload, "credential_string"

    if is_verifiable_credential(payload):
        return payload, "credential_json"

    if (payload.get("beneficiaryId") or payload.get("subjectId") or payload.get("enrollmentCode")) and payload.get("recordType") == "RefuPassPrintablePass":
        return payload, "printable_pass_qr"

    if (payload.get("beneficiaryId") or payload.get("subjectId") or payload.get("enrollmentCode")) and payload.get("programName"):
        return payload, "printable_pass_qr"

    raise HTTPException(
        status_code=400,
        detail="Verification payload must be Verifiable Credential JSON, a credential QR string, or a RefuPass printable-pass QR payload",
    )


def merge_lookup_payload(target: dict[str, Any], source: dict[str, Any] | None) -> dict[str, Any]:
    if not source:
        return target

    for key, value in source.items():
        if value in (None, "", [], {}):
            continue
        if key == "credentialSubject" and isinstance(value, dict):
            subject = target.setdefault("credentialSubject", {})
            if isinstance(subject, dict):
                for nested_key, nested_value in value.items():
                    if nested_value not in (None, "", [], {}) and not subject.get(nested_key):
                        subject[nested_key] = nested_value
            continue
        if key not in target or target.get(key) in (None, "", [], {}):
            target[key] = value
    return target


def build_lookup_payload(
    payload: dict[str, Any] | str,
    credential_metadata: dict[str, Any] | None,
    verified_claims: dict[str, Any] | None,
) -> dict[str, Any]:
    lookup_payload: dict[str, Any] = {}
    if isinstance(payload, dict):
        merge_lookup_payload(lookup_payload, payload)
    merge_lookup_payload(lookup_payload, credential_metadata)
    merge_lookup_payload(lookup_payload, verified_claims)
    return lookup_payload


def find_enrollment_from_payload(
    db: Session,
    payload: dict[str, Any],
    explicit_program_enrollment_id: int | None,
    ngo_id: int,
) -> ProgramEnrollment | None:
    if explicit_program_enrollment_id:
        return db.scalar(
            select(ProgramEnrollment)
            .join(Program, Program.id == ProgramEnrollment.program_id)
            .options(
                joinedload(ProgramEnrollment.person).joinedload(Person.household),
                joinedload(ProgramEnrollment.program).joinedload(Program.ngo),
            )
            .where(ProgramEnrollment.id == explicit_program_enrollment_id, Program.ngo_id == ngo_id)
        )

    subject = payload.get("credentialSubject") or {}
    candidate_values = [
        subject.get("beneficiaryId"),
        subject.get("subjectId"),
        subject.get("id"),
        payload.get("beneficiaryId"),
        payload.get("subjectId"),
        payload.get("enrollmentCode"),
        payload.get("personCode"),
    ]
    program_name = payload.get("programName") or subject.get("programName")
    for candidate in candidate_values:
        if not candidate:
            continue
        enrollment = db.scalar(
            select(ProgramEnrollment)
            .join(Person, Person.id == ProgramEnrollment.person_id)
            .join(Program, Program.id == ProgramEnrollment.program_id)
            .options(
                joinedload(ProgramEnrollment.person).joinedload(Person.household),
                joinedload(ProgramEnrollment.program).joinedload(Program.ngo),
            )
            .where(
                Program.ngo_id == ngo_id,
                or_(
                    Person.auth_subject == str(candidate),
                    Person.person_code == str(candidate),
                    ProgramEnrollment.enrollment_code == str(candidate),
                ),
            )
        )
        if enrollment:
            if program_name and enrollment.program.name != program_name:
                continue
            return enrollment
    return None


def determine_business_status(
    cryptographic_status: str,
    enrollment: ProgramEnrollment | None,
    eligibility: Eligibility | None,
    redemption: Redemption | None,
    payload: dict[str, Any],
    *,
    allow_business_only: bool = False,
) -> tuple[str, bool]:
    if cryptographic_status != "valid":
        if allow_business_only and cryptographic_status == "not_checked":
            pass
        else:
            return "invalid", False
    if not enrollment:
        return "unrecognized_enrollment", False
    if not eligibility or eligibility.status != "eligible":
        return "ineligible", False

    subject = payload.get("credentialSubject") or {}
    expiration_text = payload.get("expirationDate") or payload.get("validUntil") or subject.get("validUntil")
    if expiration_text:
        try:
            expiration = date.fromisoformat(expiration_text.replace("Z", "").split("T")[0])
        except ValueError:
            expiration = eligibility.valid_until
        if expiration < date.today():
            return "expired", False

    if redemption:
        return "already_redeemed", False

    return "valid", True


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/platform/ngos", response_model=list[PlatformNgoSummary])
def list_platform_ngos(
    _user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
) -> list[PlatformNgoSummary]:
    ngos = (
        db.scalars(
            select(Ngo)
            .options(
                joinedload(Ngo.users),
                joinedload(Ngo.programs).joinedload(Program.enrollments),
            )
            .order_by(Ngo.name.asc())
        )
        .unique()
        .all()
    )
    return [serialize_platform_ngo(ngo) for ngo in ngos]


@app.post("/platform/ngos", response_model=PlatformNgoSummary, status_code=status.HTTP_201_CREATED)
def create_platform_ngo(
    payload: AdminRegisterRequest,
    _user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
) -> PlatformNgoSummary:
    existing_ngo = db.scalar(select(Ngo).where(Ngo.name == payload.ngo_name))
    if existing_ngo:
        raise HTTPException(status_code=400, detail="An NGO with this name already exists")

    existing_user = db.scalar(select(User).where(User.username == payload.username))
    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already in use")

    ngo = Ngo(name=payload.ngo_name)
    ngo_admin = User(
        username=payload.username,
        password=payload.password,
        role="ngo_admin",
        display_name=payload.admin_display_name,
        ngo=ngo,
    )
    db.add_all([ngo, ngo_admin])
    db.commit()
    ngo = (
        db.scalars(
            select(Ngo)
            .options(
                joinedload(Ngo.users),
                joinedload(Ngo.programs).joinedload(Program.enrollments),
            )
            .where(Ngo.id == ngo.id)
        )
        .unique()
        .one()
    )
    return serialize_platform_ngo(ngo)


@app.post(
    "/platform/identity-verifications",
    response_model=IdentityVerificationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_identity_verification(
    payload: IdentityVerificationStartRequest,
    _user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
) -> IdentityVerificationSessionResponse:
    verification_session = IdentityVerificationSession(
        session_token=str(uuid4()),
        provider="esignet",
        status="pending",
        state="pending",
        nonce="pending",
        client_id="pending",
        code_verifier="pending",
        private_key_pem="pending",
        authorize_url="pending",
        person_payload=payload.model_dump(),
    )
    try:
        session_details = await esignet_service.start_verification(session_token=verification_session.session_token)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "RefuPass could not reach the local eSignet stack. "
                f"Expected UI at {settings.esignet_ui_url} and API at {settings.esignet_api_url}. "
                "Start Experiments/esignet-compose before verifying a person."
            ),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    verification_session.state = session_details["state"]
    verification_session.nonce = session_details["nonce"]
    verification_session.client_id = session_details["client_id"]
    verification_session.code_verifier = session_details["code_verifier"]
    verification_session.private_key_pem = session_details["private_key_pem"]
    verification_session.authorize_url = session_details["authorize_url"]
    db.add(verification_session)
    db.commit()
    return IdentityVerificationSessionResponse(
        session_token=verification_session.session_token,
        status=verification_session.status,
        provider=verification_session.provider,
        authorize_url=verification_session.authorize_url,
    )


@app.get("/platform/identity-verifications/{session_token}", response_model=IdentityVerificationSessionStatus)
def get_identity_verification_status(
    session_token: str,
    _user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
) -> IdentityVerificationSessionStatus:
    verification_session = db.scalar(
        select(IdentityVerificationSession).where(IdentityVerificationSession.session_token == session_token)
    )
    if not verification_session:
        raise HTTPException(status_code=404, detail="Identity verification session not found")
    return serialize_identity_verification_session(db, verification_session)


@app.get("/platform/identity/esignet/callback", response_class=HTMLResponse)
async def complete_identity_verification(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if not state:
        return HTMLResponse("<h1>RefuPass verification failed</h1><p>Missing state.</p>", status_code=400)

    verification_session = db.scalar(
        select(IdentityVerificationSession).where(IdentityVerificationSession.state == state)
    )
    if not verification_session:
        return HTMLResponse("<h1>RefuPass verification failed</h1><p>Unknown verification session.</p>", status_code=404)

    if error:
        verification_session.status = "failed"
        verification_session.error_message = error
        verification_session.completed_at = datetime.now(timezone.utc)
        db.commit()
        return HTMLResponse(
            "<script>window.close();</script><h1>Verification cancelled</h1><p>You can close this window.</p>",
            status_code=200,
        )

    if not code:
        verification_session.status = "failed"
        verification_session.error_message = "Missing authorization code"
        verification_session.completed_at = datetime.now(timezone.utc)
        db.commit()
        return HTMLResponse("<h1>RefuPass verification failed</h1><p>Missing authorization code.</p>", status_code=400)

    try:
        verified_identity = await esignet_service.complete_verification(
            client_id=verification_session.client_id,
            private_key_pem=verification_session.private_key_pem,
            code_verifier=verification_session.code_verifier,
            code=code,
        )
        payload = verification_session.person_payload
        household = create_household_from_payload(
            db,
            household_code=payload["household_code"],
            family_size=payload["family_size"],
            primary_contact_name=payload["primary_contact_name"],
            settlement=payload["settlement"],
        )
        person = create_or_reuse_person(
            db,
            person_code=None,
            auth_subject=verified_identity["auth_subject"],
            full_name=payload["full_name"],
            phone=payload.get("phone"),
            gender=payload.get("gender"),
            identity_status="verified_digital",
            identity_provider=verified_identity["identity_provider"],
            verified_at=datetime.now(timezone.utc),
            household=household,
        )
        verification_session.status = "completed"
        verification_session.verified_subject = verified_identity["auth_subject"]
        verification_session.person_id = person.id
        verification_session.completed_at = datetime.now(timezone.utc)
        verification_session.error_message = None
        db.commit()
        return HTMLResponse(
            "<script>window.close();</script><h1>Verification complete</h1><p>You can close this window.</p>",
            status_code=200,
        )
    except Exception as exc:
        db.rollback()
        verification_session = db.scalar(
            select(IdentityVerificationSession).where(IdentityVerificationSession.id == verification_session.id)
        )
        verification_session.status = "failed"
        verification_session.error_message = str(exc)
        verification_session.completed_at = datetime.now(timezone.utc)
        db.commit()
        return HTMLResponse(
            "<h1>RefuPass verification failed</h1><p>Check the platform dashboard for details.</p>",
            status_code=500,
        )


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).options(joinedload(User.ngo)).where(User.username == payload.username))
    if not user or user.password != payload.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(
        access_token=build_access_token(user),
        role=user.role,
        display_name=user.display_name,
        ngo_name=user.ngo.name if user.ngo else None,
    )


@app.get("/aid-cycles/current", response_model=AidCycleResponse)
def get_current_cycle(
    _user: User = Depends(require_role("ngo_admin", "aid_worker")),
    db: Session = Depends(get_db),
) -> AidCycleResponse:
    return AidCycleResponse.model_validate(get_current_cycle_record(db))


@app.get("/aid-workers", response_model=list[StaffUserResponse])
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


@app.post("/aid-workers", response_model=StaffUserResponse, status_code=status.HTTP_201_CREATED)
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


@app.get("/people", response_model=list[PersonSummary])
def list_people(
    search: str | None = None,
    _user: User = Depends(require_role("platform_admin", "ngo_admin")),
    db: Session = Depends(get_db),
) -> list[PersonSummary]:
    query = select(Person).options(joinedload(Person.household)).order_by(Person.full_name.asc())
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                Person.full_name.ilike(pattern),
                Person.auth_subject.ilike(pattern),
                Person.person_code.ilike(pattern),
            )
        )
    people = db.scalars(query).all()
    return [serialize_person(person) for person in people]


@app.get("/program-enrollments", response_model=list[ProgramEnrollmentSummary])
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


@app.post("/program-enrollments", response_model=ProgramEnrollmentSummary, status_code=status.HTTP_201_CREATED)
def create_program_enrollment(
    payload: ProgramEnrollmentCreate,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> ProgramEnrollmentSummary:
    person = get_person_or_404(db, payload.person_id)
    program = get_or_create_program(
        db,
        ngo_id=user.ngo_id,
        name=payload.program_name,
        assistance_type=payload.assistance_type,
        distribution_site=payload.distribution_site,
        ration_tier=payload.ration_tier,
    )
    enrollment = create_or_reuse_program_enrollment(
        db,
        person=person,
        program=program,
        distribution_site=payload.distribution_site,
        ration_tier=payload.ration_tier,
        created_by_user_id=user.id,
        notes=payload.notes,
    )
    db.commit()
    enrollment = get_program_enrollment_for_ngo_or_404(db, enrollment.id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    return serialize_program_enrollment(db, enrollment, aid_cycle)


@app.get("/program-enrollments/{enrollment_id}", response_model=ProgramEnrollmentDetail)
def get_program_enrollment(
    enrollment_id: int,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> ProgramEnrollmentDetail:
    enrollment = get_program_enrollment_for_ngo_or_404(db, enrollment_id, user.ngo_id)
    aid_cycle = get_current_cycle_record(db)
    return serialize_program_enrollment_detail(db, enrollment, aid_cycle)


@app.patch("/program-enrollments/{enrollment_id}/eligibility", response_model=EligibilitySnapshot)
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


@app.post("/issuance-sessions", response_model=IssuanceSessionResponse, status_code=status.HTTP_201_CREATED)
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

    session_token, session_payload = build_issuance_payload(enrollment, eligibility, aid_cycle, settings)
    entitlement = get_or_create_entitlement(
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


@app.get("/issuance-sessions/{session_token}", response_model=IssuanceSessionResponse)
def get_issuance_session(
    session_token: str,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> IssuanceSessionResponse:
    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    aid_cycle = issuance_session.aid_cycle or get_current_cycle_record(db)
    return serialize_issuance_session(db, issuance_session, enrollment, aid_cycle)


@app.patch("/issuance-sessions/{session_token}/status", response_model=IssuanceSessionResponse)
def update_issuance_session_status(
    session_token: str,
    payload: IssuanceSessionStatusUpdate,
    user: User = Depends(require_role("ngo_admin")),
    db: Session = Depends(get_db),
) -> IssuanceSessionResponse:
    allowed_statuses = {"holder_in_progress", "wallet_window_closed"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unsupported issuance session status")

    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    if issuance_session.status not in {"entitlement_ready", "holder_in_progress", "wallet_window_closed"}:
        raise HTTPException(status_code=400, detail="Issuance session can no longer be updated from the admin popup flow")

    issuance_session.status = payload.status
    db.commit()
    issuance_session, enrollment = get_issuance_session_for_ngo_or_404(db, session_token, user.ngo_id)
    aid_cycle = issuance_session.aid_cycle or get_current_cycle_record(db)
    return serialize_issuance_session(db, issuance_session, enrollment, aid_cycle)


@app.post("/worker/verify", response_model=WorkerVerifyResponse)
async def worker_verify(
    payload: WorkerVerifyRequest,
    user: User = Depends(require_role("aid_worker")),
    db: Session = Depends(get_db),
) -> WorkerVerifyResponse:
    verification_payload, verification_mode = parse_verification_payload(payload)
    if verification_mode in {"credential_json", "credential_string"}:
        verification = await verify_client.verify(verification_payload)
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
        and verification_mode in {"credential_json", "credential_string"}
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
            subject_id=enrollment.person.auth_subject or "",
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


@app.post("/worker/redeem", response_model=RedemptionResponse, status_code=status.HTTP_201_CREATED)
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
        issuer_id="RefuPassFoodAid",
        credential_configuration_id="RefuPassFoodAidCredential",
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


@app.get("/redemptions", response_model=list[RedemptionResponse])
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


@app.post("/grievances", response_model=GrievanceResponse, status_code=status.HTTP_201_CREATED)
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


@app.get("/grievances", response_model=list[GrievanceResponse])
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
