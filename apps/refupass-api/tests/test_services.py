from __future__ import annotations

import json

from sqlalchemy import select

from app.main import (
    determine_business_status,
    get_current_cycle_record,
    get_current_eligibility_for_enrollment,
)
from app.models import ProgramEnrollment
from app.services.issuance import build_credential_preview, build_printable_pass
from app.services.pass_tokens import verify_pass_payload


def test_build_credential_preview_uses_enrollment_and_cycle_fields(db_session) -> None:
    enrollment = db_session.scalar(select(ProgramEnrollment).where(ProgramEnrollment.enrollment_code == "ENR-001"))
    aid_cycle = get_current_cycle_record(db_session)
    eligibility = get_current_eligibility_for_enrollment(db_session, enrollment.id, aid_cycle.id)

    preview = build_credential_preview(enrollment, eligibility, aid_cycle)

    assert preview.subject_id == "PER-001"
    assert preview.person_code == "PER-001"
    assert preview.enrollment_code == "ENR-001"
    assert preview.household_id == "HH-001"
    assert preview.aid_cycle == "March 2026 Food Assistance"
    assert preview.entitlement_status == "eligible"


def test_build_printable_pass_contains_worker_qr_payload(db_session) -> None:
    enrollment = db_session.scalar(select(ProgramEnrollment).where(ProgramEnrollment.enrollment_code == "ENR-001"))
    aid_cycle = get_current_cycle_record(db_session)
    eligibility = get_current_eligibility_for_enrollment(db_session, enrollment.id, aid_cycle.id)

    printable_pass = build_printable_pass(enrollment, eligibility, aid_cycle)
    payload = json.loads(printable_pass.qr_payload)

    assert payload["recordType"] == "RefuPassPrintablePass"
    assert payload["verificationMode"] == "refupass_pass_qr"
    assert payload["enrollmentCode"] == "ENR-001"
    assert verify_pass_payload(payload, "refupass-demo-pass-signing-secret") is True


def test_determine_business_status_accepts_printable_pass_business_checks_only(db_session) -> None:
    enrollment = db_session.scalar(select(ProgramEnrollment).where(ProgramEnrollment.enrollment_code == "ENR-001"))
    aid_cycle = get_current_cycle_record(db_session)
    eligibility = get_current_eligibility_for_enrollment(db_session, enrollment.id, aid_cycle.id)

    status, can_redeem = determine_business_status(
        "not_checked",
        enrollment,
        eligibility,
        None,
        {"subjectId": "5860356276", "validUntil": "2026-03-31"},
        allow_business_only=True,
    )

    assert status == "valid"
    assert can_redeem is True
