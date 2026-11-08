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


def _similar(a: str, b: str) -> bool:
    return a == b or SequenceMatcher(None, a, b).ratio() >= TOKEN_SIMILARITY


def name_matches(account_name: str, official_name: str) -> bool:
    """Each word of the account name (at least two words) must match a *different* word on the
    NIN record, in any order. Extra official names (e.g. a middle name) are fine. Matching is
    one-to-one, so "Kemi Kemi" can't use the record's single "KEMI" twice."""
    mine, theirs = _tokens(account_name), _tokens(official_name)
    if len(mine) < 2 or len(mine) > len(theirs):
        return False
    owner: dict[int, int] = {}  # official index -> account index (bipartite matching)

    def place(i: int, seen: set[int]) -> bool:
        for j, official in enumerate(theirs):
            if j in seen or not _similar(mine[i], official):
                continue
            seen.add(j)
            if j not in owner or place(owner[j], seen):
                owner[j] = i
                return True
        return False

    return all(place(i, set()) for i in range(len(mine)))


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
