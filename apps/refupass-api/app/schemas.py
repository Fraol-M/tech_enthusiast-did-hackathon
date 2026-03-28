from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


class HealthResponse(ApiModel):
    status: str


class LoginRequest(ApiModel):
    username: str
    password: str


class LoginResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str
    ngo_name: str


class NgoSummary(ApiModel):
    id: int
    name: str


class AidCycleResponse(ApiModel):
    id: int
    name: str
    starts_on: date
    ends_on: date
    is_current: bool


class HouseholdSummary(ApiModel):
    id: int
    household_code: str
    family_size: int
    primary_contact_name: str
    settlement: str


class EligibilitySnapshot(ApiModel):
    id: int
    status: str
    notes: str | None = None
    valid_from: date
    valid_until: date


class RedemptionResponse(ApiModel):
    id: int
    beneficiary_id: int
    aid_cycle_id: int
    worker_username: str
    verification_reference: str
    delivery_status: str
    notes: str | None = None
    created_at: datetime


class GrievanceResponse(ApiModel):
    id: int
    beneficiary_id: int
    aid_cycle_id: int
    created_by: str
    reason: str
    details: str
    status: str
    redemption_id: int | None = None
    created_at: datetime


class BeneficiarySummary(ApiModel):
    id: int
    beneficiary_code: str
    auth_subject: str
    full_name: str
    phone: str
    gender: str
    identity_status: str
    identity_provider: str | None = None
    verified_at: datetime | None = None
    program_name: str
    distribution_site: str
    ration_tier: str
    ngo: NgoSummary
    household: HouseholdSummary
    current_eligibility: EligibilitySnapshot | None = None
    current_redemption: RedemptionResponse | None = None


class BeneficiaryDetail(BeneficiarySummary):
    redemptions: list[RedemptionResponse] = Field(default_factory=list)
    grievances: list[GrievanceResponse] = Field(default_factory=list)


class BeneficiaryCreate(ApiModel):
    beneficiary_code: str
    auth_subject: str
    full_name: str
    phone: str
    gender: str
    program_name: str
    distribution_site: str
    ration_tier: str
    household_code: str
    family_size: int
    primary_contact_name: str
    settlement: str


class AdminRegisterRequest(ApiModel):
    ngo_name: str
    admin_display_name: str
    username: str
    password: str


class AidWorkerCreate(ApiModel):
    display_name: str
    username: str
    password: str


class StaffUserResponse(ApiModel):
    id: int
    username: str
    role: str
    display_name: str
    ngo_name: str


class EligibilityUpdate(ApiModel):
    status: str
    notes: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None


class PrintablePass(ApiModel):
    beneficiary_code: str
    full_name: str
    program_name: str
    aid_cycle: str
    distribution_site: str
    family_size: int
    ration_tier: str
    valid_until: date
    qr_payload: str


class CredentialPreview(ApiModel):
    beneficiary_id: str
    household_id: str
    full_name: str
    program_name: str
    aid_cycle: str
    distribution_site: str
    family_size: int
    ration_tier: str
    entitlement_status: str
    valid_from: date
    valid_until: date


class IssuanceSessionRequest(ApiModel):
    beneficiary_id: int


class IssuanceSessionResponse(ApiModel):
    session_token: str
    issuer_id: str
    credential_configuration_id: str
    launch_url: str
    status: str
    instructions: list[str]
    credential_preview: CredentialPreview
    printable_pass: PrintablePass


class WorkerVerifyRequest(ApiModel):
    credential: dict[str, Any] | None = None
    credential_text: str | None = None
    beneficiary_id: int | None = None


class WorkerBeneficiarySummary(ApiModel):
    record_id: int
    beneficiary_code: str
    beneficiary_id: str
    household_id: str
    full_name: str
    family_size: int
    program_name: str
    ration_tier: str


class WorkerVerifyResponse(ApiModel):
    verification_mode: str
    cryptographic_status: str
    business_status: str
    beneficiary_summary: WorkerBeneficiarySummary | None = None
    aid_cycle: str | None = None
    distribution_site: str | None = None
    can_redeem: bool
    verification_reference: str
    details: dict[str, Any] = Field(default_factory=dict)


class RedeemRequest(ApiModel):
    beneficiary_id: int
    verification_reference: str
    notes: str | None = None


class GrievanceCreate(ApiModel):
    beneficiary_id: int
    reason: str
    details: str
    redemption_id: int | None = None
    aid_cycle_id: int | None = None
