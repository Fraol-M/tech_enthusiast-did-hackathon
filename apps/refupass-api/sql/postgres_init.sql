CREATE SCHEMA IF NOT EXISTS refupass;

CREATE TABLE IF NOT EXISTS refupass.households (
    id SERIAL PRIMARY KEY,
    household_code VARCHAR(50) UNIQUE NOT NULL,
    family_size INTEGER NOT NULL,
    primary_contact_name VARCHAR(120) NOT NULL,
    settlement VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refupass.beneficiaries (
    id SERIAL PRIMARY KEY,
    beneficiary_code VARCHAR(50) UNIQUE NOT NULL,
    auth_subject VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    gender VARCHAR(20) NOT NULL,
    program_name VARCHAR(120) NOT NULL,
    distribution_site VARCHAR(120) NOT NULL,
    ration_tier VARCHAR(60) NOT NULL,
    household_id INTEGER NOT NULL REFERENCES refupass.households(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refupass.aid_cycles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) UNIQUE NOT NULL,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refupass.eligibility (
    id SERIAL PRIMARY KEY,
    beneficiary_id INTEGER NOT NULL REFERENCES refupass.beneficiaries(id),
    aid_cycle_id INTEGER NOT NULL REFERENCES refupass.aid_cycles(id),
    status VARCHAR(20) NOT NULL,
    notes TEXT,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_refupass_eligibility UNIQUE (beneficiary_id, aid_cycle_id)
);

CREATE TABLE IF NOT EXISTS refupass.redemptions (
    id SERIAL PRIMARY KEY,
    beneficiary_id INTEGER NOT NULL REFERENCES refupass.beneficiaries(id),
    aid_cycle_id INTEGER NOT NULL REFERENCES refupass.aid_cycles(id),
    worker_username VARCHAR(50) NOT NULL,
    verification_reference VARCHAR(120) NOT NULL,
    delivery_status VARCHAR(30) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_refupass_redemption UNIQUE (beneficiary_id, aid_cycle_id)
);

CREATE TABLE IF NOT EXISTS refupass.grievances (
    id SERIAL PRIMARY KEY,
    beneficiary_id INTEGER NOT NULL REFERENCES refupass.beneficiaries(id),
    aid_cycle_id INTEGER NOT NULL REFERENCES refupass.aid_cycles(id),
    created_by VARCHAR(50) NOT NULL,
    reason VARCHAR(120) NOT NULL,
    details TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    redemption_id INTEGER REFERENCES refupass.redemptions(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO refupass.households (household_code, family_size, primary_contact_name, settlement)
VALUES ('HH-001', 5, 'Amina Hassan', 'Kebribeyah Camp')
ON CONFLICT (household_code) DO NOTHING;

INSERT INTO refupass.aid_cycles (name, starts_on, ends_on, is_current)
VALUES ('March 2026 Food Assistance', DATE '2026-03-01', DATE '2026-03-31', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO refupass.beneficiaries (
    beneficiary_code,
    auth_subject,
    full_name,
    phone,
    gender,
    program_name,
    distribution_site,
    ration_tier,
    household_id
)
SELECT
    'BEN-001',
    '5860356276',
    'Amina Hassan',
    '+251911000111',
    'female',
    'Emergency Food Assistance',
    'Kebribeyah Site A',
    'Standard Family Ration',
    households.id
FROM refupass.households households
WHERE households.household_code = 'HH-001'
ON CONFLICT (beneficiary_code) DO NOTHING;

INSERT INTO refupass.eligibility (beneficiary_id, aid_cycle_id, status, notes, valid_from, valid_until)
SELECT
    beneficiaries.id,
    aid_cycles.id,
    'eligible',
    'Approved after household verification.',
    aid_cycles.starts_on,
    aid_cycles.ends_on
FROM refupass.beneficiaries beneficiaries
JOIN refupass.aid_cycles aid_cycles ON aid_cycles.name = 'March 2026 Food Assistance'
WHERE beneficiaries.beneficiary_code = 'BEN-001'
ON CONFLICT (beneficiary_id, aid_cycle_id) DO NOTHING;

CREATE OR REPLACE VIEW refupass.issuance_candidates AS
SELECT
    beneficiaries.auth_subject AS id,
    beneficiaries.auth_subject AS beneficiaryId,
    households.household_code AS householdId,
    beneficiaries.full_name AS fullName,
    beneficiaries.program_name AS programName,
    aid_cycles.name AS aidCycle,
    beneficiaries.distribution_site AS distributionSite,
    households.family_size AS familySize,
    beneficiaries.ration_tier AS rationTier,
    eligibility.status AS entitlementStatus,
    eligibility.valid_from AS validFrom,
    eligibility.valid_until AS validUntil
FROM refupass.beneficiaries beneficiaries
JOIN refupass.households households ON households.id = beneficiaries.household_id
JOIN refupass.eligibility eligibility ON eligibility.beneficiary_id = beneficiaries.id
JOIN refupass.aid_cycles aid_cycles ON aid_cycles.id = eligibility.aid_cycle_id;
