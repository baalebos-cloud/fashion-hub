"""
Authentication business logic: signup, login, email verification,
password reset, refresh-token rotation.

Kept independent of FastAPI (no Request/Response objects) so it's fully
unit-testable with a plain SQLAlchemy Session.
"""
import hashlib
from datetime import datetime, timedelta, timezone  # Added timezone-aware tracking utilities
from typing import Optional

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings  # Imported settings for token expiry metrics
from app.core.constants import UserRole
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshSession, User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def sign_up(self, *, email: str, phone_number: Optional[str], password: str, full_name: str, role: str) -> User:
        if role not in {r.value for r in UserRole}:
            raise ValidationAppError(f"Invalid role '{role}'.")

        if self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists.")
        if phone_number and self.users.get_by_phone(phone_number):
            raise ConflictError("An account with this phone number already exists.")

        user = User(
            email=email.lower().strip(),
            phone_number=phone_number,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Fire-and-forget: actual sending happens in a background worker
        # (see workers/email_tasks.py) so signup stays fast.
        from app.workers.email_tasks import send_verification_email_task
        token = create_email_verification_token(str(user.id))
        send_verification_email_task.delay(user_email=user.email, token=token)

        return user

    def log_in(self, *, email: str, password: str, user_agent: Optional[str], ip_address: Optional[str]) -> dict:
        user = self.users.get_by_email(email.lower().strip())
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))

        # Dynamic expiry window creation derived from settings config metrics
        expiry_date = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = RefreshSession(
            user_id=user.id,
            refresh_token_hash=self._hash_token(refresh_token),
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expiry_date,  # Fixed: Populated instead of passing None
        )
        self.db.add(session)
        self.db.commit()

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": user}

    def refresh_access_token(self, refresh_token: str) -> str:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except (JWTError, ValueError):
            raise UnauthorizedError("Invalid or expired refresh token.")

        token_hash = self._hash_token(refresh_token)
        session = (
            self.db.query(RefreshSession)
            .filter(RefreshSession.refresh_token_hash == token_hash, RefreshSession.revoked.is_(False))
            .first()
        )
        if not session:
            raise UnauthorizedError("Refresh token has been revoked or does not exist.")

        user = self.users.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")

        return create_access_token(str(user.id), user.role)

    def log_out(self, refresh_token: str) -> None:
        token_hash = self._hash_token(refresh_token)
        session = self.db.query(RefreshSession).filter(RefreshSession.refresh_token_hash == token_hash).first()
        if session:
            session.revoked = True
            self.db.commit()

    def verify_email(self, token: str) -> None:
        try:
            payload = decode_token(token, expected_type="email_verification")
        except (JWTError, ValueError):
            raise ValidationAppError("Invalid or expired verification token.")

        user = self.users.get_by_id(payload["sub"])
        if not user:
            raise ValidationAppError("User not found.")
        user.is_email_verified = True
        self.db.commit()

    def request_password_reset(self, email: str) -> None:
        user = self.users.get_by_email(email.lower().strip())
        if not user:
            # Do not reveal whether the email exists.
            return
        from app.workers.email_tasks import send_password_reset_email_task
        token = create_password_reset_token(str(user.id))
        send_password_reset_email_task.delay(user_email=user.email, token=token)

    def reset_password(self, *, token: str, new_password: str) -> None:
        try:
            payload = decode_token(token, expected_type="password_reset")
        except (JWTError, ValueError):
            raise ValidationAppError("Invalid or expired reset token.")

        user = self.users.get_by_id(payload["sub"])
        if not user:
            raise ValidationAppError("User not found.")
        user.hashed_password = hash_password(new_password)

        user = self.users.get_by_id(payload["sub"])
        if not user:
            raise ValidationAppError("User not found.")
        user.hashed_password = hash_password(new_password)
        self.db.commit()
        # Revoke all existing sessions on password change.
        self.db.query(RefreshSession).filter(RefreshSession.user_id == user.id).update({"revoked": True})
        self.db.commit()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

