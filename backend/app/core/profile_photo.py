"""Riders, vendors, tailors and designers must show a real profile photo; customers may skip it.

Customers meet these people in person (at pickup, at the door, at fittings), so a face or
business photo on their profile is part of trust and safety. Enforced when they submit
verification and when an admin approves it.
"""
from app.core.exceptions import ValidationAppError

PHOTO_REQUIRED_ROLES = {"tailor", "designer", "vendor", "delivery_partner"}


def photo_required(role: str | None) -> bool:
    return role in PHOTO_REQUIRED_ROLES


def has_photo(user) -> bool:
    return bool((getattr(user, "profile_photo_url", None) or "").strip())


def require_profile_photo(user, *, message: str | None = None) -> None:
    if photo_required(getattr(user, "role", None)) and not has_photo(user):
        raise ValidationAppError(message or "Add a clear profile photo before submitting verification.")
