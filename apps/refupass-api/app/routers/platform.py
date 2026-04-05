from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import runtime
from ..database import get_db
from ..domain.operations import generate_reference
from ..domain.operations import create_household_from_payload, create_or_reuse_person
from ..domain.serializers import serialize_identity_verification_session, serialize_platform_ngo
from ..models import IdentityVerificationSession, Ngo, Person, Program, User
from ..schemas import (
    AdminRegisterRequest,
    IdentityVerificationSessionResponse,
    IdentityVerificationSessionStatus,
    IdentityVerificationStartRequest,
    PlatformNgoSummary,
)
from ..security import get_password_hash, require_role


router = APIRouter()


@router.get("/platform/ngos", response_model=list[PlatformNgoSummary])
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


@router.post("/platform/ngos", response_model=PlatformNgoSummary, status_code=status.HTTP_201_CREATED)
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
        password=get_password_hash(payload.password),
        role=payload.role,
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


@router.post(
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
        session_details = await runtime.esignet_service.start_verification(session_token=verification_session.session_token)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "RefuPass could not reach the local eSignet stack. "
                f"Expected UI at {runtime.settings.esignet_ui_url} and API at {runtime.settings.esignet_api_url}. "
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


@router.get("/platform/identity-verifications/{session_token}", response_model=IdentityVerificationSessionStatus)
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


@router.get("/platform/identity/esignet/callback", response_class=HTMLResponse)
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
        verified_identity = await runtime.esignet_service.complete_verification(
            client_id=verification_session.client_id,
            private_key_pem=verification_session.private_key_pem,
            code_verifier=verification_session.code_verifier,
            code=code,
        )
        payload = verification_session.person_payload
        existing_person = db.scalar(select(Person.id).where(Person.auth_subject == verified_identity["auth_subject"]))
        household_code = payload.get("household_code") or generate_reference("HH")
        primary_contact_name = payload.get("primary_contact_name") or payload["full_name"]
        household = create_household_from_payload(
            db,
            household_code=household_code,
            family_size=payload["family_size"],
            primary_contact_name=primary_contact_name,
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
        verification_session.person_payload = {
            **payload,
            "verification_outcome": "existing_person" if existing_person else "created_person",
        }
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
