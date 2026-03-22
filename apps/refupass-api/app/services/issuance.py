from __future__ import annotations

import json
import uuid

from ..config import Settings
from ..models import AidCycle, Beneficiary, Eligibility
from ..schemas import CredentialPreview, PrintablePass


def build_credential_preview(beneficiary: Beneficiary, eligibility: Eligibility, aid_cycle: AidCycle) -> CredentialPreview:
    return CredentialPreview(
        beneficiary_id=beneficiary.auth_subject,
        household_id=beneficiary.household.household_code,
        full_name=beneficiary.full_name,
        program_name=beneficiary.program_name,
        aid_cycle=aid_cycle.name,
        distribution_site=beneficiary.distribution_site,
        family_size=beneficiary.household.family_size,
        ration_tier=beneficiary.ration_tier,
        entitlement_status=eligibility.status,
        valid_from=eligibility.valid_from,
        valid_until=eligibility.valid_until,
    )


def build_printable_pass(beneficiary: Beneficiary, eligibility: Eligibility, aid_cycle: AidCycle) -> PrintablePass:
    qr_payload = json.dumps(
        {
            "recordType": "RefuPassPrintablePass",
            "verificationMode": "printable_pass_qr",
            "beneficiaryId": beneficiary.auth_subject,
            "beneficiaryCode": beneficiary.beneficiary_code,
            "householdId": beneficiary.household.household_code,
            "fullName": beneficiary.full_name,
            "programName": beneficiary.program_name,
            "aidCycle": aid_cycle.name,
            "distributionSite": beneficiary.distribution_site,
            "familySize": beneficiary.household.family_size,
            "rationTier": beneficiary.ration_tier,
            "entitlementStatus": eligibility.status,
            "validUntil": eligibility.valid_until.isoformat(),
        }
    )
    return PrintablePass(
        beneficiary_code=beneficiary.beneficiary_code,
        full_name=beneficiary.full_name,
        program_name=beneficiary.program_name,
        aid_cycle=aid_cycle.name,
        distribution_site=beneficiary.distribution_site,
        family_size=beneficiary.household.family_size,
        ration_tier=beneficiary.ration_tier,
        valid_until=eligibility.valid_until,
        qr_payload=qr_payload,
    )


def build_issuance_payload(
    beneficiary: Beneficiary,
    eligibility: Eligibility,
    aid_cycle: AidCycle,
    settings: Settings,
) -> tuple[str, dict]:
    session_token = str(uuid.uuid4())
    qr_payload = {
        "beneficiaryId": beneficiary.auth_subject,
        "householdId": beneficiary.household.household_code,
        "programName": beneficiary.program_name,
        "aidCycle": aid_cycle.name,
        "distributionSite": beneficiary.distribution_site,
        "familySize": beneficiary.household.family_size,
        "rationTier": beneficiary.ration_tier,
        "entitlementStatus": eligibility.status,
        "validFrom": eligibility.valid_from.isoformat(),
        "validUntil": eligibility.valid_until.isoformat(),
        "sessionToken": session_token,
    }
    return session_token, {
        "launch_url": settings.inji_web_url,
        "issuer_id": "RefuPassFoodAid",
        "credential_configuration_id": "RefuPassFoodAidCredential",
        "status": "created",
        "instructions": [
            "Open the existing Inji Web holder flow.",
            "Authenticate the beneficiary with the working eSignet mock path.",
            "Download the RefuPassFoodAidCredential into the holder wallet.",
            "Use the printable fallback only when the holder device is unavailable.",
        ],
        "credential_preview": build_credential_preview(beneficiary, eligibility, aid_cycle),
        "printable_pass": build_printable_pass(beneficiary, eligibility, aid_cycle),
        "qr_payload": qr_payload,
    }
