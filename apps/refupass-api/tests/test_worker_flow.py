from __future__ import annotations

import json

from fastapi.testclient import TestClient
from app import runtime


def test_worker_verify_printable_pass_is_redeemable(
    client: TestClient,
    worker_headers: dict[str, str],
    printable_pass_payload: str,
) -> None:
    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": printable_pass_payload},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verificationMode"] == "refupass_pass_qr"
    assert payload["cryptographicStatus"] == "valid"
    assert payload["businessStatus"] == "valid"
    assert payload["canRedeem"] is True
    assert payload["enrollmentSummary"]["enrollmentCode"] == "ENR-001"


def test_worker_redeem_then_verify_again_returns_already_redeemed(
    client: TestClient,
    worker_headers: dict[str, str],
    printable_pass_payload: str,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    issuance_session = client.post(
        "/issuance-sessions",
        headers=ngo_admin_headers,
        json={"programEnrollmentId": enrollment_ids["ENR-001"]},
    )
    session_token = issuance_session.json()["sessionToken"]
    first_verify = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": printable_pass_payload},
    )
    verification_reference = first_verify.json()["verificationReference"]
    enrollment_id = first_verify.json()["enrollmentSummary"]["recordId"]

    redeem = client.post(
        "/worker/redeem",
        headers=worker_headers,
        json={
            "programEnrollmentId": enrollment_id,
            "verificationReference": verification_reference,
            "notes": "Delivered at site",
        },
    )
    second_verify = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": printable_pass_payload},
    )
    updated_session = client.get(f"/issuance-sessions/{session_token}", headers=ngo_admin_headers)

    assert redeem.status_code == 201
    assert second_verify.status_code == 200
    assert redeem.json()["programEnrollmentId"] is not None
    assert redeem.json()["entitlementId"] is not None
    assert second_verify.json()["businessStatus"] == "already_redeemed"
    assert second_verify.json()["canRedeem"] is False
    assert updated_session.status_code == 200
    assert updated_session.json()["status"] == "redeemed"


def test_worker_verify_credential_json_uses_cryptographic_stub(
    client: TestClient,
    worker_headers: dict[str, str],
    credential_payload: dict,
    ngo_admin_headers: dict[str, str],
    enrollment_ids: dict[str, int],
) -> None:
    issuance_session = client.post(
        "/issuance-sessions",
        headers=ngo_admin_headers,
        json={"programEnrollmentId": enrollment_ids["ENR-001"]},
    )
    session_token = issuance_session.json()["sessionToken"]

    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credential": credential_payload},
    )
    updated_session = client.get(f"/issuance-sessions/{session_token}", headers=ngo_admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["verificationMode"] == "credential_json"
    assert payload["cryptographicStatus"] == "valid"
    assert payload["businessStatus"] == "valid"
    assert payload["details"]["mode"] == "stub"
    assert updated_session.status_code == 200
    assert updated_session.json()["status"] == "credential_verified"


def test_worker_verify_raw_string_returns_invalid_in_stub_mode(client: TestClient, worker_headers: dict[str, str]) -> None:
    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": "opaque-credential-qr-string"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verificationMode"] == "credential_string"
    assert payload["cryptographicStatus"] == "invalid"
    assert payload["businessStatus"] == "invalid"


def test_worker_verify_credential_string_with_metadata_resolves_enrollment(
    client: TestClient,
    worker_headers: dict[str, str],
    monkeypatch,
) -> None:
    class FakeVerifyClient:
        async def verify(self, _credential):
            return {
                "cryptographicStatus": "valid",
                "details": {
                    "mode": "passthrough",
                    "claims": {
                        "subjectId": "5860356276",
                        "programName": "Emergency Food Assistance",
                        "validUntil": "2028-03-29T00:00:00Z",
                    },
                },
            }

    monkeypatch.setattr(runtime, "verify_client", FakeVerifyClient())

    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={
            "credentialText": "opaque-credential-qr-string",
            "credentialMetadata": {
                "subjectId": "5860356276",
                "programName": "Emergency Food Assistance",
                "validUntil": "2028-03-29T00:00:00Z",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verificationMode"] == "credential_string"
    assert payload["cryptographicStatus"] == "valid"
    assert payload["businessStatus"] == "valid"
    assert payload["enrollmentSummary"]["enrollmentCode"] == "ENR-001"


def test_worker_can_open_grievance(client: TestClient, worker_headers: dict[str, str], printable_pass_payload: str) -> None:
    verify = client.post("/worker/verify", headers=worker_headers, json={"credentialText": printable_pass_payload})
    enrollment_id = verify.json()["enrollmentSummary"]["recordId"]

    response = client.post(
        "/grievances",
        headers=worker_headers,
        json={
            "programEnrollmentId": enrollment_id,
            "reason": "Card unreadable",
            "details": "QR code could not be scanned at the distribution desk.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["reason"] == "Card unreadable"
    assert payload["status"] == "open"
    assert payload["personId"] is not None
    assert payload["programEnrollmentId"] is not None


def test_redemptions_and_grievances_lists_include_new_records(
    client: TestClient,
    worker_headers: dict[str, str],
    printable_pass_payload: str,
) -> None:
    verify = client.post("/worker/verify", headers=worker_headers, json={"credentialText": printable_pass_payload})
    enrollment_id = verify.json()["enrollmentSummary"]["recordId"]
    verification_reference = verify.json()["verificationReference"]

    redeem = client.post(
        "/worker/redeem",
        headers=worker_headers,
        json={
            "programEnrollmentId": enrollment_id,
            "verificationReference": verification_reference,
            "notes": "Delivered during list test.",
        },
    )
    grievance = client.post(
        "/grievances",
        headers=worker_headers,
        json={
            "programEnrollmentId": enrollment_id,
            "reason": "Follow-up needed",
            "details": "Worker requested a post-delivery follow-up.",
        },
    )
    redemptions = client.get("/redemptions", headers=worker_headers)
    grievances = client.get("/grievances", headers=worker_headers)

    assert redeem.status_code == 201
    assert grievance.status_code == 201
    assert redemptions.status_code == 200
    assert grievances.status_code == 200
    assert any(item["verificationReference"] == verification_reference for item in redemptions.json())
    assert any(item["reason"] == "Follow-up needed" for item in grievances.json())


def test_printable_pass_payload_matches_seeded_beneficiary(printable_pass_payload: str) -> None:
    payload = json.loads(printable_pass_payload)

    assert payload["recordType"] == "RefuPassPrintablePass"
    assert payload["verificationMode"] == "refupass_pass_qr"
    assert payload["subjectId"] == "PER-001"
    assert payload["enrollmentCode"] == "ENR-001"
    assert payload["programName"] == "Emergency Food Assistance"


def test_worker_rejects_tampered_refupass_pass(
    client: TestClient,
    worker_headers: dict[str, str],
    printable_pass_payload: str,
) -> None:
    payload = json.loads(printable_pass_payload)
    payload["fullName"] = "Tampered Person"

    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": json.dumps(payload)},
    )

    assert response.status_code == 200
    assert response.json()["verificationMode"] == "refupass_pass_qr"
    assert response.json()["cryptographicStatus"] == "invalid"
    assert response.json()["businessStatus"] == "invalid"
