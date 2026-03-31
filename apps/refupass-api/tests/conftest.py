from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import main
from app.database import Base
from app.main import get_current_cycle_record, get_current_eligibility_for_enrollment
from app.models import ProgramEnrollment
from app.seed import seed_demo_data
from app.services.issuance import build_printable_pass
from app.services.verify_client import InjiVerifyClient


class FakeESignetVerificationService:
    async def start_verification(self, *, session_token: str) -> dict[str, str]:
        return {
            "session_token": session_token,
            "state": f"state-{session_token}",
            "nonce": f"nonce-{session_token}",
            "client_id": "fake-esignet-client",
            "private_key_pem": "fake-private-key",
            "code_verifier": "fake-code-verifier",
            "authorize_url": f"http://mock-esignet.local/authorize?session={session_token}",
        }

    async def complete_verification(
        self,
        *,
        client_id: str,
        private_key_pem: str,
        code_verifier: str,
        code: str,
    ) -> dict[str, str]:
        assert client_id == "fake-esignet-client"
        assert private_key_pem == "fake-private-key"
        assert code_verifier == "fake-code-verifier"
        return {
            "auth_subject": code,
            "identity_provider": "esignet_mock",
        }


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "refupass-test.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.create_all(bind=test_engine)
    with TestingSessionLocal() as db:
        seed_demo_data(db)

    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(
        main,
        "verify_client",
        InjiVerifyClient(SimpleNamespace(inji_verify_mode="stub", inji_verify_api_url="http://unused")),
    )
    monkeypatch.setattr(main, "esignet_service", FakeESignetVerificationService())

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture
def platform_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ngo_admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "ngoadmin", "password": "ngo123"})
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def worker_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "aidworker", "password": "worker123"})
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enrollment_ids(client: TestClient, ngo_admin_headers: dict[str, str]) -> dict[str, int]:
    response = client.get("/program-enrollments", headers=ngo_admin_headers)
    enrollments = response.json()
    return {item["enrollmentCode"]: item["id"] for item in enrollments}


@pytest.fixture
def printable_pass_payload(client: TestClient, ngo_admin_headers: dict[str, str], enrollment_ids: dict[str, int]) -> str:
    override_get_db = next(iter(client.app.dependency_overrides.values()))
    generator = override_get_db()
    db = next(generator)
    try:
        enrollment = db.scalar(select(ProgramEnrollment).where(ProgramEnrollment.id == enrollment_ids["ENR-001"]))
        aid_cycle = get_current_cycle_record(db)
        eligibility = get_current_eligibility_for_enrollment(db, enrollment.id, aid_cycle.id)
        return build_printable_pass(enrollment, eligibility, aid_cycle).qr_payload
    finally:
        db.close()


@pytest.fixture
def credential_payload() -> dict:
    return {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "RefuPassFoodAidCredential"],
        "credentialSubject": {
            "subjectId": "5860356276",
            "fullName": "Amina Hassan",
        },
        "proof": {"type": "Ed25519Signature2020"},
    }


@pytest.fixture
def db_session(client: TestClient):
    override_get_db = next(iter(client.app.dependency_overrides.values()))
    generator = override_get_db()
    db = next(generator)
    try:
        yield db
    finally:
        db.close()
