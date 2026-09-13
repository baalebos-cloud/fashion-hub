"""Reusable input validators beyond what Pydantic field types cover."""
import re

PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")  # loose E.164-ish check


def is_valid_phone_number(value: str) -> bool:
    return bool(PHONE_RE.match(value))
