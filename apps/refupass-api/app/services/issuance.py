from __future__ import annotations

import json
import uuid

from ..config import Settings
from ..models import AidCycle, Eligibility, ProgramEnrollment
from ..schemas import CredentialPreview, ExternalWalletFlow, PrintablePass


def build_issuance_instructions() -> list[str]:
    return [
        "RefuPass has prepared this entitlement for the already-verified shared person.",
        "NGO staff can now coordinate holder delivery without repeating RefuPass enrollment or eligibility checks.",
        "The external wallet path below is a local-stack compatibility flow and may still ask the holder to authenticate again.",
    ]


def build_external_wallet_flow(settings: Settings) -> ExternalWalletFlow:
    return ExternalWalletFlow(
        mode="authorization_code_compatibility",
        label="Continue in wallet popup",
        url=settings.inji_web_url,
        requires_identity_reauthentication=True,
        note="This local Inji setup still uses the wallet's authorization-code flow. RefuPass will track popup progress, but the wallet flow may still ask the holder to authenticate again.",
    )


def build_credential_preview(enrollment: ProgramEnrollment, eligibility: Eligibility, aid_cycle: AidCycle) -> CredentialPreview:
    person = enrollment.person
    household = person.household
    program = enrollment.program
    return CredentialPreview(
        subject_id=person.auth_subject or "",
        person_code=person.person_code,
        enrollment_code=enrollment.enrollment_code,
        household_id=household.household_code if household else "",
        full_name=person.full_name,
        program_name=program.name,
        aid_cycle=aid_cycle.name,
        distribution_site=enrollment.distribution_site,
        family_size=household.family_size if household else 0,
        ration_tier=enrollment.ration_tier,
        entitlement_status=eligibility.status,
        valid_from=eligibility.valid_from,
        valid_until=eligibility.valid_until,
    )


def build_printable_pass(enrollment: ProgramEnrollment, eligibility: Eligibility, aid_cycle: AidCycle) -> PrintablePass:
    person = enrollment.person
    household = person.household
    program = enrollment.program
    qr_payload = json.dumps(
        {
            "recordType": "RefuPassPrintablePass",
            "verificationMode": "printable_pass_qr",
            "subjectId": person.auth_subject,
            "personCode": person.person_code,
            "enrollmentCode": enrollment.enrollment_code,
            "householdId": household.household_code if household else "",
            "fullName": person.full_name,
            "programName": program.name,
            "aidCycle": aid_cycle.name,
            "distributionSite": enrollment.distribution_site,
            "familySize": household.family_size if household else 0,
            "rationTier": enrollment.ration_tier,
            "entitlementStatus": eligibility.status,
            "validUntil": eligibility.valid_until.isoformat(),
        }
    )
    return PrintablePass(
        enrollment_code=enrollment.enrollment_code,
        person_code=person.person_code,
        full_name=person.full_name,
        program_name=program.name,
        aid_cycle=aid_cycle.name,
        distribution_site=enrollment.distribution_site,
        family_size=household.family_size if household else 0,
        ration_tier=enrollment.ration_tier,
        valid_until=eligibility.valid_until,
        qr_payload=qr_payload,
    )


def build_issuance_payload(
    enrollment: ProgramEnrollment,
    eligibility: Eligibility,
    aid_cycle: AidCycle,
    settings: Settings,
) -> tuple[str, dict]:
    person = enrollment.person
    household = person.household
    program = enrollment.program
    session_token = str(uuid.uuid4())
    qr_payload = {
        "subjectId": person.auth_subject,
        "personCode": person.person_code,
        "enrollmentCode": enrollment.enrollment_code,
        "householdId": household.household_code if household else "",
        "programName": program.name,
        "aidCycle": aid_cycle.name,
        "distributionSite": enrollment.distribution_site,
        "familySize": household.family_size if household else 0,
        "rationTier": enrollment.ration_tier,
        "entitlementStatus": eligibility.status,
        "validFrom": eligibility.valid_from.isoformat(),
        "validUntil": eligibility.valid_until.isoformat(),
        "sessionToken": session_token,
    }
    return session_token, {
        "launch_url": settings.inji_web_url,
        "issuer_id": "RefuPassFoodAid",
        "credential_configuration_id": "RefuPassFoodAidCredential",
        "status": "entitlement_ready",
        "flow_type": "issuer_managed",
        "instructions": build_issuance_instructions(),
        "credential_preview": build_credential_preview(enrollment, eligibility, aid_cycle),
        "external_wallet_flow": build_external_wallet_flow(settings),
        "qr_payload": qr_payload,
    }
