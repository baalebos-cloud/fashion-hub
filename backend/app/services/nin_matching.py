"""Rules for approving an identity check without an admin.

Every rule must pass. Anything else goes to an admin with the failed rules listed; nothing here
rejects a person automatically.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

TOKEN_SIMILARITY = 0.85  # allows a one-letter typo in a longer name, not a different name


def _tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z]+", text) if len(t) >= 2]


def name_matches(account_name: str, official_name: str) -> bool:
    """Each word of the account name (at least two words) must match a word on the NIN record,
    in any order. Extra official names (e.g. a middle name) are fine."""
    mine, theirs = _tokens(account_name), _tokens(official_name)
    if len(mine) < 2 or not theirs:
        return False
    return all(any(t == o or SequenceMatcher(None, t, o).ratio() >= TOKEN_SIMILARITY for o in theirs) for t in mine)


def evaluate(*, account_name: str, official_name: str | None, entered_dob: date | None, official_dob: date | None,
             has_photo: bool, duplicate: bool) -> dict:
    """Return each rule's result plus an overall verdict. No personal data in the output."""
    checks = {
        "record_found": official_name is not None,
        "name_matches": bool(official_name) and name_matches(account_name, official_name),
        "date_of_birth_matches": entered_dob is not None and official_dob is not None and entered_dob == official_dob,
        "profile_photo": has_photo,
        "nin_not_used_elsewhere": not duplicate,
    }
    return {"checks": checks, "passed": all(checks.values())}
