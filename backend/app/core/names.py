"""A person's name in three parts: first name, middle name (optional) and surname.

`users.full_name` is still kept, always built from the parts, because emails, receipts, the
NIN check and older app versions all read it. Accounts made before the parts existed have
their parts filled in by splitting the full name (migration 0040, or `split_full_name`).
"""
import re
import unicodedata

from app.core.exceptions import ValidationAppError

MAX_PART = 80
# Letters in any alphabet (with accents and tone marks, e.g. Yoruba "Adébáyọ̀"), plus the marks names
# really use: spaces, hyphens, apostrophes and full stops.
_LETTERS = r"(?:[^\W\d_]|[\u0300-\u036f])+"
_ALLOWED = re.compile(rf"^{_LETTERS}(?:[ .'’-]+{_LETTERS})*\.?$")


def clean_part(value: str | None, *, label: str, required: bool) -> str | None:
    """Trim and tidy one part of a name; refuse anything that isn't a plausible name."""
    text = unicodedata.normalize("NFC", re.sub(r"\s+", " ", (value or "")).strip())
    if not text:
        if required:
            raise ValidationAppError(f"Enter your {label}.")
        return None
    if len(text) > MAX_PART:
        raise ValidationAppError(f"Your {label} is too long ({MAX_PART} characters at most).")
    if not _ALLOWED.match(text):
        raise ValidationAppError(f"Your {label} can only contain letters, spaces, hyphens and apostrophes.")
    return text


def compose_full_name(first: str, middle: str | None, last: str) -> str:
    return " ".join(part for part in (first, middle, last) if part)


def split_full_name(full_name: str | None) -> tuple[str | None, str | None, str | None]:
    """Best guess for an older account: first word, last word, and everything between."""
    words = (full_name or "").split()
    if not words:
        return None, None, None
    if len(words) == 1:
        return words[0][:MAX_PART], None, None
    middle = " ".join(words[1:-1]) or None
    return words[0][:MAX_PART], (middle[:MAX_PART] if middle else None), words[-1][:MAX_PART]
