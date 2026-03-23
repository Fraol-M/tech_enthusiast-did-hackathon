from __future__ import annotations

import json

from fastapi.testclient import TestClient


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
    assert payload["verificationMode"] == "printable_pass_qr"
    assert payload["cryptographicStatus"] == "not_checked"
    assert payload["businessStatus"] == "valid"
    assert payload["canRedeem"] is True
    assert payload["beneficiarySummary"]["beneficiaryCode"] == "BEN-001"


def test_worker_redeem_then_verify_again_returns_already_redeemed(
    client: TestClient,
    worker_headers: dict[str, str],
    printable_pass_payload: str,
) -> None:
    first_verify = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": printable_pass_payload},
    )
    verification_reference = first_verify.json()["verificationReference"]
    beneficiary_id = first_verify.json()["beneficiarySummary"]["recordId"]

    redeem = client.post(
        "/worker/redeem",
        headers=worker_headers,
        json={
            "beneficiaryId": beneficiary_id,
            "verificationReference": verification_reference,
            "notes": "Delivered at site",
        },
    )
    second_verify = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": printable_pass_payload},
    )

    assert redeem.status_code == 201
    assert second_verify.status_code == 200
    assert second_verify.json()["businessStatus"] == "already_redeemed"
    assert second_verify.json()["canRedeem"] is False


def test_worker_verify_credential_json_uses_cryptographic_stub(
    client: TestClient,
    worker_headers: dict[str, str],
    credential_payload: dict,
) -> None:
    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credential": credential_payload},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verificationMode"] == "credential_json"
    assert payload["cryptographicStatus"] == "valid"
    assert payload["businessStatus"] == "valid"
    assert payload["details"]["mode"] == "stub"


def test_worker_verify_rejects_invalid_json_text(client: TestClient, worker_headers: dict[str, str]) -> None:
    response = client.post(
        "/worker/verify",
        headers=worker_headers,
        json={"credentialText": "{not-valid-json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Credential text is not valid JSON"


def test_worker_can_open_grievance(client: TestClient, worker_headers: dict[str, str], printable_pass_payload: str) -> None:
    verify = client.post("/worker/verify", headers=worker_headers, json={"credentialText": printable_pass_payload})
    beneficiary_id = verify.json()["beneficiarySummary"]["recordId"]

    response = client.post(
        "/grievances",
        headers=worker_headers,
        json={
            "beneficiaryId": beneficiary_id,
            "reason": "Card unreadable",
            "details": "QR code could not be scanned at the distribution desk.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["reason"] == "Card unreadable"
    assert payload["status"] == "open"


def test_redemptions_and_grievances_lists_include_new_records(
    client: TestClient,
    worker_headers: dict[str, str],
    printable_pass_payload: str,
) -> None:
    verify = client.post("/worker/verify", headers=worker_headers, json={"credentialText": printable_pass_payload})
    beneficiary_id = verify.json()["beneficiarySummary"]["recordId"]
    verification_reference = verify.json()["verificationReference"]

    redeem = client.post(
        "/worker/redeem",
        headers=worker_headers,
        json={
            "beneficiaryId": beneficiary_id,
            "verificationReference": verification_reference,
            "notes": "Delivered during list test.",
        },
    )
    grievance = client.post(
        "/grievances",
        headers=worker_headers,
        json={
            "beneficiaryId": beneficiary_id,
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
    assert payload["beneficiaryId"] == "5860356276"
    assert payload["programName"] == "Emergency Food Assistance"
