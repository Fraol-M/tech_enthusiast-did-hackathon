from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_access_token(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "admin"
    assert payload["displayName"] == "NGO Admin"
    assert payload["ngoName"] == "Relief Alliance Ethiopia"
    assert payload["accessToken"].startswith("demo:admin:")


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_beneficiaries_require_authentication(client: TestClient) -> None:
    response = client.get("/beneficiaries")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_current_cycle_returns_seeded_cycle(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/aid-cycles/current", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "March 2026 Food Assistance"
    assert response.json()["isCurrent"] is True


def test_beneficiary_detail_returns_household_and_history(
    client: TestClient,
    admin_headers: dict[str, str],
    beneficiary_ids: dict[str, int],
) -> None:
    response = client.get(f"/beneficiaries/{beneficiary_ids['BEN-001']}", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["beneficiaryCode"] == "BEN-001"
    assert payload["ngo"]["name"] == "Relief Alliance Ethiopia"
    assert payload["household"]["householdCode"] == "HH-001"
    assert len(payload["redemptions"]) == 1
    assert payload["redemptions"][0]["verificationReference"] == "seed-redemption-feb-2026"


def test_admin_can_create_beneficiary(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/beneficiaries",
        headers=admin_headers,
        json={
            "beneficiaryCode": "BEN-003",
            "authSubject": "1111222233",
            "fullName": "Nura Ali",
            "phone": "+251900123456",
            "gender": "female",
            "programName": "Emergency Food Assistance",
            "distributionSite": "Kebribeyah Site C",
            "rationTier": "Child Nutrition Support",
            "householdCode": "HH-003",
            "familySize": 3,
            "primaryContactName": "Nura Ali",
            "settlement": "Kebribeyah Camp",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["beneficiaryCode"] == "BEN-003"
    assert payload["identityStatus"] == "record_only"
    assert payload["ngo"]["name"] == "Relief Alliance Ethiopia"
    assert payload["household"]["householdCode"] == "HH-003"
    assert payload["currentEligibility"] is None


def test_can_register_new_ngo_admin(client: TestClient) -> None:
    response = client.post(
        "/auth/register-admin",
        json={
            "ngoName": "Frontier Relief",
            "adminDisplayName": "Marta Ayele",
            "username": "marta-admin",
            "password": "safe-pass-123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["role"] == "admin"
    assert payload["displayName"] == "Marta Ayele"
    assert payload["ngoName"] == "Frontier Relief"


def test_admin_can_register_aid_worker(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/aid-workers",
        headers=admin_headers,
        json={
            "displayName": "Lulit Kassa",
            "username": "lulit-worker",
            "password": "field-pass-123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["role"] == "aid_worker"
    assert payload["displayName"] == "Lulit Kassa"
    assert payload["ngoName"] == "Relief Alliance Ethiopia"


def test_admin_can_list_only_their_own_aid_workers(client: TestClient, admin_headers: dict[str, str]) -> None:
    register_response = client.post(
        "/auth/register-admin",
        json={
            "ngoName": "Harbor Response",
            "adminDisplayName": "Sara Noor",
            "username": "sara-admin",
            "password": "harbor-123",
        },
    )
    other_admin_token = register_response.json()["accessToken"]
    other_headers = {"Authorization": f"Bearer {other_admin_token}"}
    client.post(
        "/aid-workers",
        headers=other_headers,
        json={
            "displayName": "Other Worker",
            "username": "other-worker",
            "password": "worker-pass",
        },
    )

    response = client.get("/aid-workers", headers=admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert all(worker["ngoName"] == "Relief Alliance Ethiopia" for worker in payload)
    assert all(worker["username"] != "other-worker" for worker in payload)


def test_worker_cannot_create_beneficiary(client: TestClient, worker_headers: dict[str, str]) -> None:
    response = client.post(
        "/beneficiaries",
        headers=worker_headers,
        json={
            "beneficiaryCode": "BEN-004",
            "authSubject": "9999000011",
            "fullName": "Blocked User",
            "phone": "+251900000000",
            "gender": "male",
            "programName": "Emergency Food Assistance",
            "distributionSite": "Site X",
            "rationTier": "Test Tier",
            "householdCode": "HH-004",
            "familySize": 1,
            "primaryContactName": "Blocked User",
            "settlement": "Transit Site",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_admin_can_update_eligibility(
    client: TestClient,
    admin_headers: dict[str, str],
    beneficiary_ids: dict[str, int],
) -> None:
    response = client.patch(
        f"/beneficiaries/{beneficiary_ids['BEN-002']}/eligibility",
        headers=admin_headers,
        json={"status": "eligible", "notes": "Manual override after review."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "eligible"
    assert payload["notes"] == "Manual override after review."


def test_worker_cannot_update_eligibility(
    client: TestClient,
    worker_headers: dict[str, str],
    beneficiary_ids: dict[str, int],
) -> None:
    response = client.patch(
        f"/beneficiaries/{beneficiary_ids['BEN-001']}/eligibility",
        headers=worker_headers,
        json={"status": "ineligible", "notes": "Blocked at field desk."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_admin_can_create_issuance_session_for_eligible_beneficiary(
    client: TestClient,
    admin_headers: dict[str, str],
    beneficiary_ids: dict[str, int],
) -> None:
    response = client.post(
        "/issuance-sessions",
        headers=admin_headers,
        json={"beneficiaryId": beneficiary_ids["BEN-001"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["issuerId"] == "RefuPassFoodAid"
    assert payload["credentialConfigurationId"] == "RefuPassFoodAidCredential"
    assert payload["credentialPreview"]["beneficiaryId"] == "5860356276"
    assert payload["printablePass"]["beneficiaryCode"] == "BEN-001"


def test_issuance_session_rejects_pending_beneficiary(
    client: TestClient,
    admin_headers: dict[str, str],
    beneficiary_ids: dict[str, int],
) -> None:
    response = client.post(
        "/issuance-sessions",
        headers=admin_headers,
        json={"beneficiaryId": beneficiary_ids["BEN-002"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Beneficiary is not eligible for the current cycle"
