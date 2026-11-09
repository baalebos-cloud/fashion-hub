"""Rules for approving a business (CAC) check without an admin.

Every rule must pass. Anything else goes to an admin with the failed rules listed; nothing here
rejects a business automatically (only a registration number CAC doesn't have is refused, earlier).
"""
from __future__ import annotations

from datetime import date

from app.integrations.kyc.prembly_cac import CACPerson
from app.services.nin_matching import name_matches

# People who can stand behind a business on the platform. A company secretary or an auditor
# is on the record but doesn't own or run the business.
NOT_OWNER_ROLES = ("SECRETARY", "AUDITOR")


def company_active(status: str | None) -> bool:
    text = (status or "").strip().upper()
    return text == "ACTIVE" or (text.startswith("ACTIVE") and "INACTIVE" not in text)


def owner_listed(people: list[CACPerson], *, verified_name: str | None, verified_dob: date | None) -> bool:
    """The person submitting (by the name and date of birth on their verified NIN) is an active
    director, proprietor, partner or shareholder on the CAC record."""
    if not verified_name:
        return False
    for person in people:
        if not person.active or (person.role and any(r in person.role for r in NOT_OWNER_ROLES)):
            continue
        if not name_matches(person.full_name, verified_name) and not name_matches(verified_name, person.full_name):
            continue
        if person.date_of_birth and verified_dob and person.date_of_birth != verified_dob:
            continue
        return True
    return False


def evaluate(*, record_found: bool, company_status: str | None, business_name_matches: bool | None,
             identity_verified: bool, people: list[CACPerson], verified_name: str | None,
             verified_dob: date | None, has_photo: bool, duplicate: bool) -> dict:
    """Each rule's result plus an overall verdict. No personal data in the output."""
    checks = {
        "record_found": record_found,
        "company_active": record_found and company_active(company_status),
        "business_name_matches": business_name_matches is True,
        "identity_verified": identity_verified,
        "owner_listed": identity_verified and owner_listed(people, verified_name=verified_name,
                                                           verified_dob=verified_dob),
        "profile_photo": has_photo,
        "registration_not_used_elsewhere": not duplicate,
    }
    return {"checks": checks, "passed": all(checks.values())}
