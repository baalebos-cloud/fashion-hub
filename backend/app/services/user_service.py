"""Generic profile management shared across all roles."""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def update_profile(self, user_id, **fields):
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")
        if "profile_photo_url" in fields and not (fields["profile_photo_url"] or "").strip():
            from app.core.profile_photo import photo_required
            if photo_required(user.role):
                from app.core.exceptions import ValidationAppError
                raise ValidationAppError("A profile photo is required for your account. Upload a new one to replace it.")
            user.profile_photo_url = None  # customers may remove their photo
            fields.pop("profile_photo_url")
        self._apply_name(user, fields)
        new_photo = (fields.get("profile_photo_url") or "").strip()
        if new_photo and new_photo != (user.profile_photo_url or "") and user.role == "tailor":
            # Photo changes are not identity checks, but the URL must still
            # resolve to an avatar uploaded by this account.
            from app.core.exceptions import ValidationAppError
            from app.services.verification_documents import read_profile_photo
            if read_profile_photo(self.db, user, new_photo) is None:
                raise ValidationAppError("Upload a profile photo through the app before saving it.")
        if new_photo and new_photo != (user.profile_photo_url or "") and user.role != "tailor":
            # Tailor profile-photo changes are ordinary media updates, not
            # identity verification. KYC submission still performs its own
            # NIN and face checks; other roles retain existing behavior.
            from app.services.kyc_service import KYCService
            KYCService(self.db).check_new_profile_photo(user, new_photo)
        for key, value in fields.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _apply_name(self, user, fields: dict) -> None:
        """Name changes: the three parts (or a single full_name from older app versions) are tidied,
        checked and saved together with the full name built from them. Pops the name keys from `fields`."""
        from app.core.names import clean_part, compose_full_name, split_full_name
        parts = {key: fields.pop(key) for key in ("first_name", "middle_name", "last_name") if key in fields}
        legacy = fields.pop("full_name", None)
        if not parts and legacy is None:
            return
        if parts:
            current = {"first_name": user.first_name, "middle_name": user.middle_name, "last_name": user.last_name}
            if not (current["first_name"] and current["last_name"]):
                current.update(zip(("first_name", "middle_name", "last_name"), split_full_name(user.full_name)))
            current.update({key: value for key, value in parts.items() if value is not None or key == "middle_name"})
            first = clean_part(current["first_name"], label="first name", required=True)
            middle = clean_part(current["middle_name"], label="middle name", required=False)
            last = clean_part(current["last_name"], label="surname", required=True)
        else:
            first, middle, last = split_full_name(" ".join(legacy.split()))
            if not first or not last:
                from app.core.exceptions import ValidationAppError
                raise ValidationAppError("Enter your first name and surname.")
            first = clean_part(first, label="first name", required=True)
            middle = clean_part(middle, label="middle name", required=False)
            last = clean_part(last, label="surname", required=True)
        full_name = compose_full_name(first, middle, last)
        if full_name != user.full_name:
            from app.services.kyc_service import KYCService
            KYCService(self.db).check_new_name(user, full_name)
        user.first_name, user.middle_name, user.last_name, user.full_name = first, middle, last, full_name

    def deactivate(self, user_id):
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")
        user.is_active = False
        self.db.commit()
        return user
