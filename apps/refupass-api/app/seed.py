from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    AidCycle,
    Eligibility,
    Entitlement,
    Grievance,
    Household,
    Ngo,
    Person,
    Program,
    ProgramEnrollment,
    Redemption,
    User,
)


def seed_demo_data(db: Session) -> None:
    existing_user = db.scalar(select(User.id).limit(1))
    if existing_user:
        return

    ngo = db.scalar(select(Ngo).where(Ngo.name == "Relief Alliance Ethiopia"))
    if not ngo:
        ngo = Ngo(name="Relief Alliance Ethiopia")

    current_cycle = AidCycle(
        name="March 2026 Food Assistance",
        starts_on=date(2026, 3, 1),
        ends_on=date(2026, 3, 31),
        is_current=True,
    )
    previous_cycle = AidCycle(
        name="February 2026 Food Assistance",
        starts_on=date(2026, 2, 1),
        ends_on=date(2026, 2, 28),
        is_current=False,
    )

    platform_admin = User(
        username="admin",
        password="admin123",
        role="platform_admin",
        display_name="RefuPass Platform Admin",
    )
    ngo_admin = User(
        username="ngoadmin",
        password="ngo123",
        role="ngo_admin",
        display_name="NGO Admin",
        ngo=ngo,
    )
    worker = User(
        username="aidworker",
        password="worker123",
        role="aid_worker",
        display_name="Aid Worker",
        ngo=ngo,
    )

    food_program = Program(
        ngo=ngo,
        name="Emergency Food Assistance",
        assistance_type="food",
        default_distribution_site="Kebribeyah Site A",
        default_ration_tier="Standard Family Ration",
        is_active=True,
    )

    household_one = Household(
        household_code="HH-001",
        family_size=5,
        primary_contact_name="Amina Hassan",
        settlement="Kebribeyah Camp",
    )
    household_two = Household(
        household_code="HH-002",
        family_size=2,
        primary_contact_name="Sami Bekele",
        settlement="Jijiga Transit Site",
    )

    person_one = Person(
        person_code="PER-001",
        auth_subject="5860356276",
        full_name="Amina Hassan",
        phone="+251911223344",
        gender="female",
        identity_status="verified_manual",
        identity_provider="seed_registry",
        household=household_one,
    )
    person_two = Person(
        person_code="PER-002",
        auth_subject="5555444433",
        full_name="Sami Bekele",
        phone="+251911334455",
        gender="male",
        identity_status="verified_manual",
        identity_provider="seed_registry",
        household=household_two,
    )

    enrollment_one = ProgramEnrollment(
        person=person_one,
        program=food_program,
        enrollment_code="ENR-001",
        status="active",
        distribution_site="Kebribeyah Site A",
        ration_tier="Standard Family Ration",
        created_by_user=ngo_admin,
        notes="Seeded food-aid enrollment.",
    )
    enrollment_two = ProgramEnrollment(
        person=person_two,
        program=food_program,
        enrollment_code="ENR-002",
        status="pending",
        distribution_site="Jijiga Site B",
        ration_tier="Single Adult Ration",
        created_by_user=ngo_admin,
        notes="Seeded pending enrollment.",
    )

    eligibility_one = Eligibility(
        program_enrollment=enrollment_one,
        aid_cycle=current_cycle,
        status="eligible",
        notes="Approved after family size review.",
        valid_from=current_cycle.starts_on,
        valid_until=current_cycle.ends_on,
    )
    eligibility_two = Eligibility(
        program_enrollment=enrollment_two,
        aid_cycle=current_cycle,
        status="pending",
        notes="Waiting for updated household verification.",
        valid_from=current_cycle.starts_on,
        valid_until=current_cycle.ends_on,
    )
    previous_eligibility = Eligibility(
        program_enrollment=enrollment_one,
        aid_cycle=previous_cycle,
        status="eligible",
        notes="Seeded history row.",
        valid_from=previous_cycle.starts_on,
        valid_until=previous_cycle.ends_on,
    )
    previous_entitlement = Entitlement(
        program_enrollment=enrollment_one,
        aid_cycle=previous_cycle,
        entitlement_code="ENT-001",
        credential_id="seed-entitlement-feb-2026",
        issuer_id="RefuPassFoodAid",
        credential_configuration_id="RefuPassFoodAidCredential",
        status="issued",
        issued_at=datetime.combine(previous_cycle.starts_on, time.min),
        expires_at=datetime.combine(previous_cycle.ends_on, time.max),
    )
    previous_redemption = Redemption(
        program_enrollment=enrollment_one,
        entitlement=previous_entitlement,
        aid_cycle=previous_cycle,
        worker_username="aidworker",
        verification_reference="seed-redemption-feb-2026",
        delivery_status="delivered",
        notes="Delivered at Site A.",
    )
    open_grievance = Grievance(
        person=person_two,
        program_enrollment=enrollment_two,
        aid_cycle=current_cycle,
        created_by="aidworker",
        reason="Identity mismatch",
        details="Person reported that the family roster has not been updated after relocation.",
        status="open",
    )

    db.add_all(
        [
            platform_admin,
            ngo_admin,
            worker,
            ngo,
            food_program,
            current_cycle,
            previous_cycle,
            household_one,
            household_two,
            person_one,
            person_two,
            enrollment_one,
            enrollment_two,
            eligibility_one,
            eligibility_two,
            previous_eligibility,
            previous_entitlement,
            previous_redemption,
            open_grievance,
        ]
    )
    db.commit()
