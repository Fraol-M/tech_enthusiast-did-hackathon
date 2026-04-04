from __future__ import annotations

import json
from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from ..models import Eligibility, Person, Program, ProgramEnrollment, Redemption


def is_verifiable_credential(payload: dict) -> bool:
    if payload.get("credentialSubject") or payload.get("proof"):
        return True
    credential_type = payload.get("type")
    if isinstance(credential_type, list):
        return "VerifiableCredential" in credential_type
    if isinstance(credential_type, str):
        return credential_type == "VerifiableCredential"
    return False


def parse_verification_payload(request) -> tuple[dict[str, Any] | str, str]:
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

    if payload.get("recordType") == "RefuPassPrintablePass" and payload.get("signature"):
        return payload, "refupass_pass_qr"

    if (payload.get("beneficiaryId") or payload.get("subjectId") or payload.get("enrollmentCode")) and payload.get("recordType") == "RefuPassPrintablePass":
        return payload, "printable_pass_qr"

    if (payload.get("beneficiaryId") or payload.get("subjectId") or payload.get("enrollmentCode")) and payload.get("programName"):
        return payload, "printable_pass_qr"

    raise HTTPException(
        status_code=400,
        detail="Verification payload must be Verifiable Credential JSON, a credential QR string, or a RefuPass pass QR payload",
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
        if expiration < eligibility.valid_from:
            return "expired", False

    if redemption:
        return "already_redeemed", False

    return "valid", True
