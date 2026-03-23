from __future__ import annotations

from sqlalchemy import select

from app.main import determine_business_status, get_current_cycle_record, get_current_eligibility
from app.models import Beneficiary
from app.services.issuance import build_credential_preview, build_printable_pass


def test_build_credential_preview_uses_beneficiary_and_cycle_fields(db_session) -> None:
    beneficiary = db_session.scalar(select(Beneficiary).where(Beneficiary.beneficiary_code == "BEN-001"))
    aid_cycle = get_current_cycle_record(db_session)
    eligibility = get_current_eligibility(db_session, beneficiary.id, aid_cycle.id)

    preview = build_credential_preview(beneficiary, eligibility, aid_cycle)

    assert preview.beneficiary_id == "5860356276"
    assert preview.household_id == "HH-001"
    assert preview.aid_cycle == "March 2026 Food Assistance"
    assert preview.entitlement_status == "eligible"


def test_build_printable_pass_contains_worker_qr_payload(db_session) -> None:
    beneficiary = db_session.scalar(select(Beneficiary).where(Beneficiary.beneficiary_code == "BEN-001"))
    aid_cycle = get_current_cycle_record(db_session)
    eligibility = get_current_eligibility(db_session, beneficiary.id, aid_cycle.id)

    printable_pass = build_printable_pass(beneficiary, eligibility, aid_cycle)

    assert '"recordType": "RefuPassPrintablePass"' in printable_pass.qr_payload
    assert '"beneficiaryCode": "BEN-001"' in printable_pass.qr_payload


def test_determine_business_status_accepts_printable_pass_business_checks_only(db_session) -> None:
    beneficiary = db_session.scalar(select(Beneficiary).where(Beneficiary.beneficiary_code == "BEN-001"))
    aid_cycle = get_current_cycle_record(db_session)
    eligibility = get_current_eligibility(db_session, beneficiary.id, aid_cycle.id)

    status, can_redeem = determine_business_status(
        "not_checked",
        beneficiary,
        eligibility,
        None,
        {"beneficiaryId": "5860356276", "validUntil": "2026-03-31"},
        allow_business_only=True,
    )

    assert status == "valid"
    assert can_redeem is True
