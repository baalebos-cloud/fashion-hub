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
