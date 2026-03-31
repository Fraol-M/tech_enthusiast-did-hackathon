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
    ngo_name: str | None = None


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


class PersonSummary(ApiModel):
    id: int
    person_code: str
    auth_subject: str | None = None
    full_name: str
    phone: str | None = None
    gender: str | None = None
    identity_status: str
    identity_provider: str | None = None
    verified_at: datetime | None = None
    household: HouseholdSummary | None = None


class PersonDetail(PersonSummary):
    enrollment_count: int = 0


class ProgramSummary(ApiModel):
    id: int
    name: str
    assistance_type: str
    default_distribution_site: str | None = None
    default_ration_tier: str | None = None
    is_active: bool
    ngo: NgoSummary


class ProgramEnrollmentSummary(ApiModel):
    id: int
    enrollment_code: str
    status: str
    distribution_site: str
    ration_tier: str
    person: PersonSummary
    program: ProgramSummary
    current_eligibility: "EligibilitySnapshot | None" = None
    current_redemption: "RedemptionResponse | None" = None
    created_at: datetime


class EligibilitySnapshot(ApiModel):
    id: int
    status: str
    notes: str | None = None
    valid_from: date
    valid_until: date


class RedemptionResponse(ApiModel):
    id: int
    program_enrollment_id: int
    entitlement_id: int
    aid_cycle_id: int
    worker_username: str
    verification_reference: str
    delivery_status: str
    notes: str | None = None
    created_at: datetime


class GrievanceResponse(ApiModel):
    id: int
    person_id: int
    program_enrollment_id: int
    aid_cycle_id: int
    created_by: str
    reason: str
    details: str
    status: str
    redemption_id: int | None = None
    created_at: datetime


class ProgramEnrollmentDetail(ProgramEnrollmentSummary):
    redemptions: list[RedemptionResponse] = Field(default_factory=list)
    grievances: list[GrievanceResponse] = Field(default_factory=list)


class IdentityVerificationStartRequest(ApiModel):
    full_name: str
    phone: str | None = None
    gender: str | None = None
    household_code: str
    family_size: int
    primary_contact_name: str
    settlement: str


class AdminRegisterRequest(ApiModel):
    ngo_name: str
    admin_display_name: str
    username: str
    password: str


class PlatformNgoSummary(ApiModel):
    id: int
    name: str
    admin_display_name: str | None = None
    admin_username: str | None = None
    aid_worker_count: int = 0
    program_count: int = 0
    enrollment_count: int = 0


class IdentityVerificationSessionResponse(ApiModel):
    session_token: str
    status: str
    provider: str
    authorize_url: str


class IdentityVerificationSessionStatus(ApiModel):
    session_token: str
    status: str
    provider: str
    verified_subject: str | None = None
    error_message: str | None = None
    person: PersonDetail | None = None


class AidWorkerCreate(ApiModel):
    display_name: str
    username: str
    password: str


class ProgramEnrollmentCreate(ApiModel):
    person_id: int
    program_name: str
    assistance_type: str = "food"
    distribution_site: str
    ration_tier: str
    notes: str | None = None


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
    enrollment_code: str
    person_code: str
    full_name: str
    program_name: str
    aid_cycle: str
    distribution_site: str
    family_size: int
    ration_tier: str
    valid_until: date
    qr_payload: str


class CredentialPreview(ApiModel):
    subject_id: str
    person_code: str
    enrollment_code: str
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


class ExternalWalletFlow(ApiModel):
    mode: str
    label: str
    url: str
    requires_identity_reauthentication: bool
    note: str


class IssuanceSessionRequest(ApiModel):
    program_enrollment_id: int


class IssuanceSessionStatusUpdate(ApiModel):
    status: str


class IssuanceSessionResponse(ApiModel):
    session_token: str
    issuer_id: str
    credential_configuration_id: str
    status: str
    flow_type: str
    instructions: list[str]
    credential_preview: CredentialPreview
    external_wallet_flow: ExternalWalletFlow | None = None


class WorkerVerifyRequest(ApiModel):
    credential: dict[str, Any] | None = None
    credential_text: str | None = None
    credential_metadata: dict[str, Any] | None = None
    program_enrollment_id: int | None = None


class WorkerEnrollmentSummary(ApiModel):
    record_id: int
    enrollment_code: str
    person_code: str
    subject_id: str
    household_id: str
    full_name: str
    family_size: int
    program_name: str
    ration_tier: str


class WorkerVerifyResponse(ApiModel):
    verification_mode: str
    cryptographic_status: str
    business_status: str
    enrollment_summary: WorkerEnrollmentSummary | None = None
    aid_cycle: str | None = None
    distribution_site: str | None = None
    can_redeem: bool
    verification_reference: str
    details: dict[str, Any] = Field(default_factory=dict)


class RedeemRequest(ApiModel):
    program_enrollment_id: int
    verification_reference: str
    notes: str | None = None


class GrievanceCreate(ApiModel):
    program_enrollment_id: int
    reason: str
    details: str
    redemption_id: int | None = None
    aid_cycle_id: int | None = None
