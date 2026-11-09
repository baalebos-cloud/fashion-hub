"""A person's name in three parts: first name, middle name (optional) and surname.

`users.full_name` is still kept, always built from the parts, because emails, receipts, the
NIN check and older app versions all read it. Accounts made before the parts existed have
their parts filled in by splitting the full name (migration 0040, or `split_full_name`).
"""
import re
import unicodedata

from app.core.exceptions import ValidationAppError

MAX_PART = 80
# Names are words of letters in any alphabet, with their accents, tone marks and vowel signs
# (Unicode categories L* and M*, e.g. "Adébáyọ̀", "राम"), joined by spaces, hyphens, apostrophes or
# full stops. Same rule as the app (lib/names.ts: [\p{L}\p{M}]).
_SEPARATORS = re.compile(r"[ .'’-]+")


def _is_word(word: str) -> bool:
    return bool(word) and all(unicodedata.category(ch)[0] in "LM" for ch in word)


def _is_name(text: str) -> bool:
    body = text[:-1] if text.endswith(".") else text  # "Jr."
    if not body or _SEPARATORS.fullmatch(body[0]) or _SEPARATORS.fullmatch(body[-1]):
        return False
    return all(_is_word(word) for word in _SEPARATORS.split(body))


def clean_part(value: str | None, *, label: str, required: bool) -> str | None:
    """Trim and tidy one part of a name; refuse anything that isn't a plausible name."""
    text = unicodedata.normalize("NFC", re.sub(r"\s+", " ", (value or "")).strip())
    if not text:
        if required:
            raise ValidationAppError(f"Enter your {label}.")
        return None
    if len(text) > MAX_PART:
        raise ValidationAppError(f"Your {label} is too long ({MAX_PART} characters at most).")
    if not _is_name(text):
        raise ValidationAppError(f"Your {label} can only contain letters, spaces, hyphens and apostrophes.")
    return text


def compose_full_name(first: str, middle: str | None, last: str) -> str:
    return " ".join(part for part in (first, middle, last) if part)


def split_full_name(full_name: str | None) -> tuple[str | None, str | None, str | None]:
    """Best guess for an older account: first word, last word, and everything between. Parts are
    returned whole; clean_part rejects any that are too long rather than cutting them."""
    words = (full_name or "").split()
    if not words:
        return None, None, None
    if len(words) == 1:
        return words[0], None, None
    return words[0], " ".join(words[1:-1]) or None, words[-1]
