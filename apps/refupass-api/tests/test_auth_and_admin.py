from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_access_and_refresh_tokens(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "platform_admin"
    assert payload["displayName"] == "RefuPass Platform Admin"
    assert payload["ngoName"] is None
    assert isinstance(payload["accessToken"], str)
    assert isinstance(payload["refreshToken"], str)
    assert payload["accessToken"] != payload["refreshToken"]
    assert payload["tokenType"] == "bearer"


def test_refresh_returns_new_access_and_refresh_tokens(client: TestClient) -> None:
    login_response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})

    response = client.post("/auth/refresh", json={"refreshToken": login_response.json()["refreshToken"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "platform_admin"
    assert isinstance(payload["accessToken"], str)
    assert isinstance(payload["refreshToken"], str)


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_program_enrollments_require_authentication(client: TestClient) -> None:
    response = client.get("/program-enrollments")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_current_cycle_returns_seeded_cycle(client: TestClient, ngo_admin_headers: dict[str, str]) -> None:
    response = client.get("/aid-cycles/current", headers=ngo_admin_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "March 2026 Food Assistance"
    assert response.json()["isCurrent"] is True


def test_program_enrollment_detail_returns_household_and_history(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    response = client.get(f"/program-enrollments/{enrollment_ids['ENR-001']}", headers=ngo_admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["enrollmentCode"] == "ENR-001"
    assert payload["program"]["ngo"]["name"] == "Relief Alliance Ethiopia"
    assert payload["person"]["household"]["householdCode"] == "HH-001"
    assert len(payload["redemptions"]) == 1
    assert payload["redemptions"][0]["verificationReference"] == "seed-redemption-feb-2026"


def test_seeded_program_enrollments_include_shared_identity_fields(client: TestClient, ngo_admin_headers: dict[str, str]) -> None:
    response = client.get("/program-enrollments", headers=ngo_admin_headers)

    assert response.status_code == 200
    amina = next(item for item in response.json() if item["enrollmentCode"] == "ENR-001")
    assert amina["person"]["id"] is not None
    assert amina["person"]["personCode"] == "PER-001"
    assert amina["currentEligibility"]["status"] == "eligible"


def test_people_search_can_match_settlement_for_ngo_enrollment(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
) -> None:
    response = client.get("/people", headers=ngo_admin_headers, params={"search": "Kebribeyah"})

    assert response.status_code == 200
    payload = response.json()
    assert any(person["fullName"] == "Amina Hassan" for person in payload)


def test_platform_admin_can_register_new_ngo_admin(
    client: TestClient,
    platform_headers: dict[str, str],
) -> None:
    response = client.post(
        "/platform/ngos",
        headers=platform_headers,
        json={
            "ngoName": "Frontier Relief",
            "adminDisplayName": "Marta Ayele",
            "username": "marta-admin",
            "password": "safe-pass-123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Frontier Relief"
    assert payload["adminDisplayName"] == "Marta Ayele"
    assert payload["adminUsername"] == "marta-admin"


def test_platform_admin_cannot_open_ngo_enrollment_console(
    client: TestClient,
    platform_headers: dict[str, str],
) -> None:
    response = client.get("/program-enrollments", headers=platform_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_platform_admin_can_start_identity_verification(client: TestClient, platform_headers: dict[str, str]) -> None:
    response = client.post(
        "/platform/identity-verifications",
        headers=platform_headers,
        json={
            "fullName": "Hawa Ahmed",
            "phone": "+251900333444",
            "gender": "female",
            "householdCode": "HH-020",
            "familySize": 4,
            "primaryContactName": "Hawa Ahmed",
            "settlement": "Kebribeyah Camp",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "esignet"
    assert payload["status"] == "pending"
    assert payload["authorizeUrl"].startswith("http://mock-esignet.local/authorize")
    assert payload["sessionToken"]


def test_platform_admin_can_start_identity_verification_without_manual_household_fields(
    client: TestClient,
    platform_headers: dict[str, str],
) -> None:
    response = client.post(
        "/platform/identity-verifications",
        headers=platform_headers,
        json={
            "fullName": "Asha Noor",
            "phone": "+251900222111",
            "gender": "female",
            "familySize": 5,
            "settlement": "Kebribeyah Camp",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["sessionToken"]


def test_ngo_admin_cannot_start_identity_verification(client: TestClient, ngo_admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/platform/identity-verifications",
        headers=ngo_admin_headers,
        json={
            "fullName": "Blocked User",
            "phone": "+251900111222",
            "gender": "female",
            "householdCode": "HH-021",
            "familySize": 2,
            "primaryContactName": "Blocked User",
            "settlement": "Kebribeyah Camp",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_manual_people_creation_route_is_not_available(client: TestClient, platform_headers: dict[str, str]) -> None:
    response = client.post("/people", headers=platform_headers, json={})

    assert response.status_code == 405


def test_ngo_admin_can_create_program_enrollment_for_existing_person(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
) -> None:
    people_response = client.get("/people", headers=ngo_admin_headers, params={"search": "Amina"})
    person_id = people_response.json()[0]["id"]

    response = client.post(
        "/program-enrollments",
        headers=ngo_admin_headers,
        json={
            "personId": person_id,
            "programName": "Nutrition Support",
            "assistanceType": "food",
            "distributionSite": "Kebribeyah Site C",
            "rationTier": "Child Nutrition Support",
            "notes": "Secondary nutrition program enrollment.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["person"]["id"] == person_id
    assert payload["program"]["name"] == "Nutrition Support"
    assert payload["program"]["ngo"]["name"] == "Relief Alliance Ethiopia"
    assert payload["distributionSite"] == "Kebribeyah Site C"


def test_ngo_admin_can_list_programs_for_structured_enrollment(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
) -> None:
    response = client.get("/programs", headers=ngo_admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert any(program["name"] == "Emergency Food Assistance" for program in payload)


def test_esignet_callback_creates_shared_person_and_status_record(
    client: TestClient,
    platform_headers: dict[str, str],
) -> None:
    verification_response = client.post(
        "/platform/identity-verifications",
        headers=platform_headers,
        json={
            "fullName": "Hawa Ahmed",
            "phone": "+251900333444",
            "gender": "female",
            "householdCode": "HH-020",
            "familySize": 4,
            "primaryContactName": "Hawa Ahmed",
            "settlement": "Kebribeyah Camp",
        },
    )
    session_token = verification_response.json()["sessionToken"]

    callback_response = client.get(
        "/platform/identity/esignet/callback",
        params={"code": "7777888899", "state": f"state-{session_token}"},
    )
    status_response = client.get(
        f"/platform/identity-verifications/{session_token}",
        headers=platform_headers,
    )

    assert callback_response.status_code == 200
    assert "Verification complete" in callback_response.text
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["status"] == "completed"
    assert payload["verifiedSubject"] == "7777888899"
    assert payload["person"]["authSubject"] == "7777888899"
    assert payload["person"]["identityStatus"] == "verified_digital"
    assert payload["person"]["identityProvider"] == "esignet_mock"


def test_new_person_enrollment_creates_program_enrollment_for_dashboard(
    client: TestClient,
    platform_headers: dict[str, str],
    ngo_admin_headers: dict[str, str],
) -> None:
    verification_response = client.post(
        "/platform/identity-verifications",
        headers=platform_headers,
        json={
            "fullName": "Nura Ali",
            "phone": "+251900123456",
            "gender": "female",
            "householdCode": "HH-030",
            "familySize": 3,
            "primaryContactName": "Nura Ali",
            "settlement": "Kebribeyah Camp",
        },
    )
    session_token = verification_response.json()["sessionToken"]
    client.get(
        "/platform/identity/esignet/callback",
        params={"code": "8888777766", "state": f"state-{session_token}"},
    )
    person_response = client.get(
        f"/platform/identity-verifications/{session_token}",
        headers=platform_headers,
    )
    person_id = person_response.json()["person"]["id"]

    enrollment_response = client.post(
        "/program-enrollments",
        headers=ngo_admin_headers,
        json={
            "personId": person_id,
            "programName": "Emergency Food Assistance",
            "assistanceType": "food",
            "distributionSite": "Kebribeyah Site C",
            "rationTier": "Family Ration",
            "notes": "Primary program enrollment.",
        },
    )

    assert enrollment_response.status_code == 201
    assert enrollment_response.json()["enrollmentCode"].startswith("ENR-")


def test_second_ngo_can_enroll_same_shared_person_without_creating_duplicate_person(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    platform_headers: dict[str, str],
) -> None:
    people_response = client.get("/people", headers=ngo_admin_headers, params={"search": "Amina"})
    shared_person = people_response.json()[0]

    client.post(
        "/platform/ngos",
        headers=platform_headers,
        json={
            "ngoName": "Frontier Relief",
            "adminDisplayName": "Marta Ayele",
            "username": "marta-admin",
            "password": "safe-pass-123",
        },
    )
    login_response = client.post(
        "/auth/login",
        json={"username": "marta-admin", "password": "safe-pass-123"},
    )
    other_headers = {"Authorization": f"Bearer {login_response.json()['accessToken']}"}

    enrollment_response = client.post(
        "/program-enrollments",
        headers=other_headers,
        json={
            "personId": shared_person["id"],
            "programName": "Emergency Cash Support",
            "assistanceType": "cash",
            "distributionSite": "Melkadida Cash Desk",
            "rationTier": "Household Cash Tier",
            "notes": "Cross-NGO enrollment for the shared person.",
        },
    )
    other_enrollments = client.get("/program-enrollments", headers=other_headers)
    people_after = client.get("/people", headers=ngo_admin_headers, params={"search": "5860356276"})

    assert enrollment_response.status_code == 201
    enrollment_payload = enrollment_response.json()
    assert enrollment_payload["person"]["id"] == shared_person["id"]
    assert enrollment_payload["program"]["ngo"]["name"] == "Frontier Relief"
    assert other_enrollments.status_code == 200
    assert any(item["person"]["id"] == shared_person["id"] for item in other_enrollments.json())
    assert len(people_after.json()) == 1


def test_ngo_admin_can_register_aid_worker(client: TestClient, ngo_admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/aid-workers",
        headers=ngo_admin_headers,
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


def test_ngo_admin_can_list_only_their_own_aid_workers(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    platform_headers: dict[str, str],
) -> None:
    client.post(
        "/platform/ngos",
        headers=platform_headers,
        json={
            "ngoName": "Harbor Response",
            "adminDisplayName": "Sara Noor",
            "username": "sara-admin",
            "password": "harbor-123",
        },
    )
    login_response = client.post(
        "/auth/login",
        json={"username": "sara-admin", "password": "harbor-123"},
    )
    other_headers = {"Authorization": f"Bearer {login_response.json()['accessToken']}"}
    client.post(
        "/aid-workers",
        headers=other_headers,
        json={
            "displayName": "Other Worker",
            "username": "other-worker",
            "password": "worker-pass",
        },
    )

    response = client.get("/aid-workers", headers=ngo_admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert all(worker["ngoName"] == "Relief Alliance Ethiopia" for worker in payload)
    assert all(worker["username"] != "other-worker" for worker in payload)


def test_worker_cannot_create_program_enrollment(client: TestClient, worker_headers: dict[str, str]) -> None:
    response = client.post(
        "/program-enrollments",
        headers=worker_headers,
        json={
            "personId": 1,
            "programName": "Emergency Food Assistance",
            "distributionSite": "Site X",
            "rationTier": "Test Tier",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_ngo_admin_can_update_eligibility(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    response = client.patch(
        f"/program-enrollments/{enrollment_ids['ENR-002']}/eligibility",
        headers=ngo_admin_headers,
        json={"status": "eligible", "notes": "Manual override after review."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "eligible"
    assert payload["notes"] == "Manual override after review."


def test_worker_cannot_update_eligibility(
    client: TestClient,
    worker_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    response = client.patch(
        f"/program-enrollments/{enrollment_ids['ENR-001']}/eligibility",
        headers=worker_headers,
        json={"status": "ineligible", "notes": "Blocked at field desk."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_ngo_admin_can_create_issuance_session_for_eligible_enrollment(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    response = client.post(
        "/issuance-sessions",
        headers=ngo_admin_headers,
        json={"programEnrollmentId": enrollment_ids["ENR-001"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["issuerId"] == "RefuPass"
    assert payload["credentialConfigurationId"] == "RefuPassPrintablePass"
    assert payload["status"] == "pass_ready"
    assert payload["flowType"] == "refupass_native_pass"
    assert payload["credentialPreview"]["subjectId"] == "PER-001"
    assert payload["passId"] == payload["sessionToken"]
    assert payload["printablePass"]["passId"] == payload["sessionToken"]
    assert payload["externalWalletFlow"] is None


def test_ngo_admin_can_fetch_update_and_download_issuance_pass(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    created = client.post(
        "/issuance-sessions",
        headers=ngo_admin_headers,
        json={"programEnrollmentId": enrollment_ids["ENR-001"]},
    )
    session_token = created.json()["sessionToken"]

    fetched = client.get(f"/issuance-sessions/{session_token}", headers=ngo_admin_headers)
    pass_response = client.get(f"/issuance-sessions/{session_token}/pass", headers=ngo_admin_headers)
    updated = client.patch(
        f"/issuance-sessions/{session_token}/status",
        headers=ngo_admin_headers,
        json={"status": "pass_downloaded"},
    )

    assert fetched.status_code == 200
    assert fetched.json()["status"] == "pass_ready"
    assert pass_response.status_code == 200
    assert pass_response.json()["passId"] == session_token
    assert updated.status_code == 200
    assert updated.json()["status"] == "pass_downloaded"


def test_issuance_session_rejects_pending_enrollment(
    client: TestClient,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    response = client.post(
        "/issuance-sessions",
        headers=ngo_admin_headers,
        json={"programEnrollmentId": enrollment_ids["ENR-002"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Enrollment is not eligible for the current cycle"
