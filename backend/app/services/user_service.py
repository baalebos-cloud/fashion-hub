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
        for key, value in fields.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user_id):
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")
        user.is_active = False
        self.db.commit()
        return user
