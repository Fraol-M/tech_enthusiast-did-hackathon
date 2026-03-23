from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import AidCycle, Beneficiary, Eligibility, Grievance, Household, IssuanceSession, Redemption, User
from .schemas import (
    AidCycleResponse,
    BeneficiaryCreate,
    BeneficiaryDetail,
    BeneficiarySummary,
    EligibilitySnapshot,
    EligibilityUpdate,
    GrievanceCreate,
    GrievanceResponse,
    HealthResponse,
    IssuanceSessionRequest,
    IssuanceSessionResponse,
    LoginRequest,
    LoginResponse,
    RedeemRequest,
    RedemptionResponse,
    WorkerBeneficiarySummary,
    WorkerVerifyRequest,
    WorkerVerifyResponse,
)
from .security import build_access_token, get_current_user, require_role
from .seed import seed_demo_data
from .services.issuance import build_issuance_payload
from .services.verify_client import InjiVerifyClient


settings = get_settings()
verify_client = InjiVerifyClient(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
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

def get_current_cycle_record(db: Session) -> AidCycle:
    cycle = db.scalar(select(AidCycle).where(AidCycle.is_current.is_(True)))
    if cycle:
        return cycle
    cycle = db.scalar(select(AidCycle).order_by(AidCycle.starts_on.desc()))
    if not cycle:
        raise HTTPException(status_code=500, detail="No aid cycle configured")
    return cycle


def get_current_eligibility(db: Session, beneficiary_id: int, aid_cycle_id: int) -> Eligibility | None:
    return db.scalar(
        select(Eligibility).where(
            Eligibility.beneficiary_id == beneficiary_id,
            Eligibility.aid_cycle_id == aid_cycle_id,
        )
    )


def get_current_redemption(db: Session, beneficiary_id: int, aid_cycle_id: int) -> Redemption | None:
    return db.scalar(
        select(Redemption).where(
            Redemption.beneficiary_id == beneficiary_id,
            Redemption.aid_cycle_id == aid_cycle_id,
        )
    )


def serialize_redemption(redemption: Redemption) -> RedemptionResponse:
    return RedemptionResponse.model_validate(redemption)


def serialize_grievance(grievance: Grievance) -> GrievanceResponse:
    return GrievanceResponse.model_validate(grievance)


def serialize_beneficiary(db: Session, beneficiary: Beneficiary, aid_cycle: AidCycle) -> BeneficiarySummary:
    current_eligibility = get_current_eligibility(db, beneficiary.id, aid_cycle.id)
    current_redemption = get_current_redemption(db, beneficiary.id, aid_cycle.id)
    return BeneficiarySummary.model_validate(
        {
            **beneficiary.__dict__,
            "household": beneficiary.household,
            "current_eligibility": current_eligibility,
            "current_redemption": current_redemption,
        }
    )


def serialize_beneficiary_detail(db: Session, beneficiary: Beneficiary, aid_cycle: AidCycle) -> BeneficiaryDetail:
    redemptions = db.scalars(
        select(Redemption)
        .where(Redemption.beneficiary_id == beneficiary.id)
        .order_by(Redemption.created_at.desc())
    ).all()
    grievances = db.scalars(
        select(Grievance)
        .where(Grievance.beneficiary_id == beneficiary.id)
        .order_by(Grievance.created_at.desc())
    ).all()
    summary = serialize_beneficiary(db, beneficiary, aid_cycle)
    return BeneficiaryDetail.model_validate(
        {
            **summary.model_dump(),
            "redemptions": redemptions,
            "grievances": grievances,
        }
    )


def is_verifiable_credential(payload: dict) -> bool:
    if payload.get("credentialSubject") or payload.get("proof"):
        return True
    credential_type = payload.get("type")
    if isinstance(credential_type, list):
        return "VerifiableCredential" in credential_type
    if isinstance(credential_type, str):
        return credential_type == "VerifiableCredential"
    return False


def parse_verification_payload(request: WorkerVerifyRequest) -> tuple[dict, str]:
    if request.credential:
        payload = request.credential
    elif request.credential_text:
        try:
            payload = json.loads(request.credential_text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Credential text is not valid JSON") from exc
    else:
        raise HTTPException(status_code=400, detail="Provide credential or credentialText")

    if is_verifiable_credential(payload):
        return payload, "credential_json"

    if payload.get("beneficiaryId") and payload.get("recordType") == "RefuPassPrintablePass":
        return payload, "printable_pass_qr"

    if payload.get("beneficiaryId") and payload.get("programName"):
        return payload, "printable_pass_qr"

    raise HTTPException(
        status_code=400,
        detail="Verification payload must be Verifiable Credential JSON or a RefuPass printable-pass QR payload",
    )


def find_beneficiary_from_payload(
    db: Session,
    payload: dict,
    explicit_beneficiary_id: int | None,
) -> Beneficiary | None:
    if explicit_beneficiary_id:
        return db.get(Beneficiary, explicit_beneficiary_id)

    subject = payload.get("credentialSubject") or {}
    candidate_values = [
        subject.get("beneficiaryId"),
        subject.get("id"),
        payload.get("beneficiaryId"),
        payload.get("beneficiaryCode"),
    ]
    for candidate in candidate_values:
        if not candidate:
            continue
        beneficiary = db.scalar(
            select(Beneficiary).where(
                or_(Beneficiary.auth_subject == str(candidate), Beneficiary.beneficiary_code == str(candidate))
            )
        )
        if beneficiary:
            return beneficiary
    return None


def determine_business_status(
    cryptographic_status: str,
    beneficiary: Beneficiary | None,
    eligibility: Eligibility | None,
    redemption: Redemption | None,
    payload: dict,
    *,
    allow_business_only: bool = False,
) -> tuple[str, bool]:
    if cryptographic_status != "valid":
        if allow_business_only and cryptographic_status == "not_checked":
            pass
        else:
            return "invalid", False
    if not beneficiary:
        return "unrecognized_beneficiary", False
    if not eligibility or eligibility.status != "eligible":
        return "ineligible", False

    subject = payload.get("credentialSubject") or {}
    expiration_text = payload.get("expirationDate") or payload.get("validUntil") or subject.get("validUntil")
    if expiration_text:
        try:
            expiration = datetime.fromisoformat(expiration_text.replace("Z", "+00:00")).date()
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


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or user.password != payload.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(
        access_token=build_access_token(user),
        role=user.role,
        display_name=user.display_name,
    )


@app.get("/aid-cycles/current", response_model=AidCycleResponse)
def get_current_cycle(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AidCycleResponse:
    return AidCycleResponse.model_validate(get_current_cycle_record(db))


@app.get("/beneficiaries", response_model=list[BeneficiarySummary])
def list_beneficiaries(
    search: str | None = None,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BeneficiarySummary]:
    aid_cycle = get_current_cycle_record(db)
    query = select(Beneficiary).options(joinedload(Beneficiary.household)).order_by(Beneficiary.full_name.asc())
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                Beneficiary.full_name.ilike(pattern),
                Beneficiary.auth_subject.ilike(pattern),
                Beneficiary.beneficiary_code.ilike(pattern),
            )
        )
    beneficiaries = db.scalars(query).all()
    return [serialize_beneficiary(db, beneficiary, aid_cycle) for beneficiary in beneficiaries]


@app.get("/beneficiaries/{beneficiary_id}", response_model=BeneficiaryDetail)
def get_beneficiary(
    beneficiary_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BeneficiaryDetail:
    beneficiary = db.scalar(
        select(Beneficiary)
        .options(joinedload(Beneficiary.household))
        .where(Beneficiary.id == beneficiary_id)
    )
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    aid_cycle = get_current_cycle_record(db)
    return serialize_beneficiary_detail(db, beneficiary, aid_cycle)


@app.post("/beneficiaries", response_model=BeneficiaryDetail, status_code=status.HTTP_201_CREATED)
def create_beneficiary(
    payload: BeneficiaryCreate,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> BeneficiaryDetail:
    household = db.scalar(select(Household).where(Household.household_code == payload.household_code))
    if not household:
        household = Household(
            household_code=payload.household_code,
            family_size=payload.family_size,
            primary_contact_name=payload.primary_contact_name,
            settlement=payload.settlement,
        )
        db.add(household)
        db.flush()

    beneficiary = Beneficiary(
        beneficiary_code=payload.beneficiary_code,
        auth_subject=payload.auth_subject,
        full_name=payload.full_name,
        phone=payload.phone,
        gender=payload.gender,
        program_name=payload.program_name,
        distribution_site=payload.distribution_site,
        ration_tier=payload.ration_tier,
        household_id=household.id,
    )
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    aid_cycle = get_current_cycle_record(db)
    return serialize_beneficiary_detail(db, beneficiary, aid_cycle)


@app.patch("/beneficiaries/{beneficiary_id}/eligibility", response_model=EligibilitySnapshot)
def update_eligibility(
    beneficiary_id: int,
    payload: EligibilityUpdate,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> EligibilitySnapshot:
    beneficiary = db.get(Beneficiary, beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    aid_cycle = get_current_cycle_record(db)
    eligibility = get_current_eligibility(db, beneficiary.id, aid_cycle.id)
    if not eligibility:
        eligibility = Eligibility(
            beneficiary_id=beneficiary.id,
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
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> IssuanceSessionResponse:
    beneficiary = db.scalar(
        select(Beneficiary)
        .options(joinedload(Beneficiary.household))
        .where(Beneficiary.id == payload.beneficiary_id)
    )
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    aid_cycle = get_current_cycle_record(db)
    eligibility = get_current_eligibility(db, beneficiary.id, aid_cycle.id)
    if not eligibility or eligibility.status != "eligible":
        raise HTTPException(status_code=400, detail="Beneficiary is not eligible for the current cycle")

    session_token, session_payload = build_issuance_payload(beneficiary, eligibility, aid_cycle, settings)
    session = IssuanceSession(
        beneficiary_id=beneficiary.id,
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
    return IssuanceSessionResponse(
        session_token=session_token,
        issuer_id=session_payload["issuer_id"],
        credential_configuration_id=session_payload["credential_configuration_id"],
        launch_url=session_payload["launch_url"],
        status=session_payload["status"],
        instructions=session_payload["instructions"],
        credential_preview=session_payload["credential_preview"],
        printable_pass=session_payload["printable_pass"],
    )


@app.post("/worker/verify", response_model=WorkerVerifyResponse)
async def worker_verify(
    payload: WorkerVerifyRequest,
    user: User = Depends(require_role("aid_worker", "admin")),
    db: Session = Depends(get_db),
) -> WorkerVerifyResponse:
    verification_payload, verification_mode = parse_verification_payload(payload)
    if verification_mode == "credential_json":
        verification = await verify_client.verify(verification_payload)
    else:
        verification = {
            "cryptographicStatus": "not_checked",
            "details": {
                "mode": verification_mode,
                "warning": "Printable-pass fallback was used; cryptographic VC verification was not performed.",
            },
        }

    beneficiary = find_beneficiary_from_payload(db, verification_payload, payload.beneficiary_id)
    aid_cycle = get_current_cycle_record(db)
    eligibility = get_current_eligibility(db, beneficiary.id, aid_cycle.id) if beneficiary else None
    redemption = get_current_redemption(db, beneficiary.id, aid_cycle.id) if beneficiary else None
    business_status, can_redeem = determine_business_status(
        verification["cryptographicStatus"],
        beneficiary,
        eligibility,
        redemption,
        verification_payload,
        allow_business_only=verification_mode == "printable_pass_qr",
    )

    beneficiary_summary = None
    if beneficiary:
        beneficiary_summary = WorkerBeneficiarySummary(
            record_id=beneficiary.id,
            beneficiary_code=beneficiary.beneficiary_code,
            beneficiary_id=beneficiary.auth_subject,
            household_id=beneficiary.household.household_code,
            full_name=beneficiary.full_name,
            family_size=beneficiary.household.family_size,
            program_name=beneficiary.program_name,
            ration_tier=beneficiary.ration_tier,
        )

    return WorkerVerifyResponse(
        verification_mode=verification_mode,
        cryptographic_status=verification["cryptographicStatus"],
        business_status=business_status,
        beneficiary_summary=beneficiary_summary,
        aid_cycle=aid_cycle.name if beneficiary else None,
        distribution_site=beneficiary.distribution_site if beneficiary else None,
        can_redeem=can_redeem,
        verification_reference=str(uuid4()),
        details={
            **verification.get("details", {}),
            "verificationMode": verification_mode,
            "verifiedBy": user.username,
            "eligibilityStatus": eligibility.status if eligibility else None,
            "redemptionStatus": redemption.delivery_status if redemption else None,
        },
    )


@app.post("/worker/redeem", response_model=RedemptionResponse, status_code=status.HTTP_201_CREATED)
def worker_redeem(
    payload: RedeemRequest,
    user: User = Depends(require_role("aid_worker", "admin")),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    beneficiary = db.get(Beneficiary, payload.beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    aid_cycle = get_current_cycle_record(db)
    existing = get_current_redemption(db, beneficiary.id, aid_cycle.id)
    if existing:
        raise HTTPException(status_code=400, detail="Current cycle already redeemed")

    eligibility = get_current_eligibility(db, beneficiary.id, aid_cycle.id)
    if not eligibility or eligibility.status != "eligible":
        raise HTTPException(status_code=400, detail="Beneficiary is not eligible for redemption")

    redemption = Redemption(
        beneficiary_id=beneficiary.id,
        aid_cycle_id=aid_cycle.id,
        worker_username=user.username,
        verification_reference=payload.verification_reference,
        delivery_status="delivered",
        notes=payload.notes,
    )
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return RedemptionResponse.model_validate(redemption)


@app.get("/redemptions", response_model=list[RedemptionResponse])
def list_redemptions(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RedemptionResponse]:
    redemptions = db.scalars(select(Redemption).order_by(Redemption.created_at.desc())).all()
    return [serialize_redemption(redemption) for redemption in redemptions]


@app.post("/grievances", response_model=GrievanceResponse, status_code=status.HTTP_201_CREATED)
def create_grievance(
    payload: GrievanceCreate,
    user: User = Depends(require_role("aid_worker", "admin")),
    db: Session = Depends(get_db),
) -> GrievanceResponse:
    beneficiary = db.get(Beneficiary, payload.beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    aid_cycle = db.get(AidCycle, payload.aid_cycle_id) if payload.aid_cycle_id else get_current_cycle_record(db)

    grievance = Grievance(
        beneficiary_id=beneficiary.id,
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
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GrievanceResponse]:
    grievances = db.scalars(select(Grievance).order_by(Grievance.created_at.desc())).all()
    return [serialize_grievance(grievance) for grievance in grievances]
