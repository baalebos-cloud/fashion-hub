"""
Repository layer isolates raw SQLAlchemy queries from service business
logic. Services never build queries directly against `db.query(...)` for
core entities -- they call a repository method instead, which keeps query
logic in one reusable, testable place.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        return self.db.query(User).filter(User.phone_number == phone_number).first()

    def add(self, user: User) -> User:
        self.db.add(user)
        return user

    def list_by_role(self, role: str, *, offset: int = 0, limit: int = 20) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.role == role, User.is_active.is_(True))
            .offset(offset)
            .limit(limit)
            .all()
        )
