from datetime import datetime
from datetime import timedelta
"""
Authentication business logic: signup, login, email verification,
password reset, refresh-token rotation.

Kept independent of FastAPI (no Request/Response objects) so it's fully
unit-testable with a plain SQLAlchemy Session.
"""
import hashlib
from typing import Optional

from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.policies import PUBLIC_SIGNUP_ROLES
from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import (
    JWTError,
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_version,
    verify_and_update_password,
)
from app.models.user import RefreshSession, User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def sign_up(self, *, email: str, phone_number: Optional[str], password: str, full_name: str, role: str, referral_code: Optional[str] = None) -> User:
        if role not in PUBLIC_SIGNUP_ROLES:
            raise ValidationAppError(f"Invalid role '{role}'.")

        email = email.lower().strip()
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

        if referral_code:
            # A bad/unknown code should never block account creation --
            # swallow validation errors from an unrecognized code rather
            # than surfacing them, since the account itself is already
            # committed above.
            from app.services.referral_service import ReferralService
            try:
                ReferralService(self.db).record_signup(referral_code=referral_code, new_user=user)
            except (ValidationAppError, ConflictError):
                pass

        # Fire-and-forget: actual sending happens in a background worker
        # (see workers/email_tasks.py) so signup stays fast.
        from app.workers.email_tasks import send_verification_email_task
        token = create_email_verification_token(str(user.id))
        send_verification_email_task.delay(user_email=user.email, token=token)

        return user

    def log_in(self, *, email: str, password: str, user_agent: Optional[str], ip_address: Optional[str]) -> dict:
        user = self.users.get_by_email(email.lower().strip())
        valid, updated_hash = verify_and_update_password(password, user.hashed_password) if user else (False, None)
        if not valid:
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        if updated_hash is not None:
            user.hashed_password = updated_hash

        access_token = create_access_token(str(user.id), user.role, {"password_version": password_version(user.hashed_password)})
        refresh_token = create_refresh_token(str(user.id))

        session = RefreshSession(
            user_id=user.id,
            refresh_token_hash=self._hash_token(refresh_token),
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(session)
        self.db.commit()

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": user}

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Consume a refresh token once and rotate its server-side session."""
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except (JWTError, ValueError):
            raise UnauthorizedError("Invalid or expired refresh token.")

        session = (self.db.query(RefreshSession)
                   .filter(RefreshSession.refresh_token_hash == self._hash_token(refresh_token))
                   .with_for_update().populate_existing().first())
        if not session or session.revoked:
            raise UnauthorizedError("Refresh token has been revoked or does not exist.")
        if session.expires_at <= datetime.utcnow() or str(session.user_id) != payload.get("sub"):
            raise UnauthorizedError("Invalid or expired refresh session.")
        user = self.users.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")

        new_refresh = create_refresh_token(str(user.id))
        session.revoked = True
        self.db.add(RefreshSession(
            user_id=user.id, refresh_token_hash=self._hash_token(new_refresh),
            user_agent=session.user_agent, ip_address=session.ip_address,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        self.db.commit()
        return {
            "access_token": create_access_token(str(user.id), user.role, {
                "password_version": password_version(user.hashed_password)
            }),
            "refresh_token": new_refresh, "token_type": "bearer",
        }

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
        token = create_password_reset_token(str(user.id), user.hashed_password)
        send_password_reset_email_task.delay(user_email=user.email, token=token)

    def reset_password(self, *, token: str, new_password: str) -> None:
        try:
            payload = decode_token(token, expected_type="password_reset")
        except (JWTError, ValueError):
            raise ValidationAppError("Invalid or expired reset token.")

        # Serialize reset attempts. Changing the hash consumes every reset link
        # issued against the previous password, including concurrent replays.
        import hmac
        user = self.db.query(User).filter(User.id == payload["sub"]).with_for_update().populate_existing().first()
        if not user or not hmac.compare_digest(payload.get("password_version", ""), password_version(user.hashed_password)):
            raise ValidationAppError("Invalid or already used reset token.")
        user.hashed_password = hash_password(new_password)
        self.db.query(RefreshSession).filter(RefreshSession.user_id == user.id).update({"revoked": True})
        self.db.commit()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
