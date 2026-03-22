from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AidCycle, Beneficiary, Eligibility, Grievance, Household, Redemption, User


def seed_demo_data(db: Session) -> None:
    existing_user = db.scalar(select(User.id).limit(1))
    if existing_user:
        return

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

    admin = User(username="admin", password="admin123", role="admin", display_name="NGO Admin")
    worker = User(username="aidworker", password="worker123", role="aid_worker", display_name="Aid Worker")

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

    beneficiary_one = Beneficiary(
        beneficiary_code="BEN-001",
        auth_subject="5860356276",
        full_name="Amina Hassan",
        phone="+251911000111",
        gender="female",
        program_name="Emergency Food Assistance",
        distribution_site="Kebribeyah Site A",
        ration_tier="Standard Family Ration",
        household=household_one,
    )
    beneficiary_two = Beneficiary(
        beneficiary_code="BEN-002",
        auth_subject="5555444433",
        full_name="Sami Bekele",
        phone="+251911000222",
        gender="male",
        program_name="Emergency Food Assistance",
        distribution_site="Jijiga Site B",
        ration_tier="Single Adult Ration",
        household=household_two,
    )

    eligibility_one = Eligibility(
        beneficiary=beneficiary_one,
        aid_cycle=current_cycle,
        status="eligible",
        notes="Approved after family size review.",
        valid_from=current_cycle.starts_on,
        valid_until=current_cycle.ends_on,
    )
    eligibility_two = Eligibility(
        beneficiary=beneficiary_two,
        aid_cycle=current_cycle,
        status="pending",
        notes="Waiting for updated household verification.",
        valid_from=current_cycle.starts_on,
        valid_until=current_cycle.ends_on,
    )
    previous_eligibility = Eligibility(
        beneficiary=beneficiary_one,
        aid_cycle=previous_cycle,
        status="eligible",
        notes="Seeded history row.",
        valid_from=previous_cycle.starts_on,
        valid_until=previous_cycle.ends_on,
    )
    previous_redemption = Redemption(
        beneficiary=beneficiary_one,
        aid_cycle=previous_cycle,
        worker_username="aidworker",
        verification_reference="seed-redemption-feb-2026",
        delivery_status="delivered",
        notes="Delivered at Site A.",
    )
    open_grievance = Grievance(
        beneficiary=beneficiary_two,
        aid_cycle=current_cycle,
        created_by="aidworker",
        reason="Identity mismatch",
        details="Beneficiary reported that the family roster has not been updated after relocation.",
        status="open",
    )

    db.add_all(
        [
            admin,
            worker,
            current_cycle,
            previous_cycle,
            household_one,
            household_two,
            beneficiary_one,
            beneficiary_two,
            eligibility_one,
            eligibility_two,
            previous_eligibility,
            previous_redemption,
            open_grievance,
        ]
    )
    db.commit()
