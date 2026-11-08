"""Two-step admin sign-in: password, then a code from an authenticator app.

Only allow-listed emails (ADMIN_EMAILS) with the admin role get through. The first sign-in
enrolls the authenticator (the secret is shown once, stored encrypted); later sign-ins need a
fresh code. Wrong passwords and wrong codes look the same to the caller.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core import totp
from app.core.admin_access import admin_email_allowed
from app.core.config import settings
from app.core.exceptions import ExternalProviderError, ForbiddenError, UnauthorizedError
from app.core.security import (
    JWTError,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    password_version,
    verify_and_update_password,
)
from app.models.activity_log import AdminCredential
from app.models.user import RefreshSession, User

CHALLENGE_MINUTES = 5
# A fresh authenticator code opens a short window for sensitive admin decisions.
STEP_UP_MINUTES = 5
GENERIC = "Invalid email, password or code."


def _cipher() -> Fernet:
    try:
        return Fernet((settings.IDENTITY_ENCRYPTION_KEY or "").encode())
    except (ValueError, TypeError) as exc:
        raise ExternalProviderError("Admin sign-in is not configured (IDENTITY_ENCRYPTION_KEY).") from exc


def _seal(secret: str) -> str:
    return "fernet:v1:" + _cipher().encrypt(secret.encode()).decode()


def _open(sealed: str) -> str:
    try:
        return _cipher().decrypt(sealed.removeprefix("fernet:v1:").encode()).decode()
    except InvalidToken as exc:
        raise ExternalProviderError("Admin sign-in secret could not be read. Reset two-step sign-in.") from exc


def active_credential_id(db: Session, user_id) -> str | None:
    """The admin's confirmed authenticator credential. Admin tokens name it, so resetting the
    authenticator (which deletes it) ends every admin session at once, not after token expiry."""
    credential = db.query(AdminCredential).filter_by(user_id=user_id).first()
    return str(credential.id) if credential and credential.totp_enabled_at else None


_DECOY: list[str] = []


def _decoy_hash() -> str:
    if not _DECOY:
        from app.core.security import hash_password
        _DECOY.append(hash_password("decoy-password-never-valid"))
    return _DECOY[0]


class AdminAuthService:
    def __init__(self, db: Session):
        self.db = db

    def _admin(self, email: str) -> User | None:
        user = self.db.query(User).filter(User.email == email.lower().strip()).first()
        if user is None or user.role != "admin" or not user.is_active or not admin_email_allowed(user.email):
            return None
        return user

    def start(self, *, email: str, password: str) -> tuple[dict, User | None]:
        user = self._admin(email)
        # Same work whether or not the account exists, so timing doesn't reveal the admin email.
        valid, updated_hash = verify_and_update_password(password, user.hashed_password if user else _decoy_hash())
        if not user or not valid:
            raise UnauthorizedError(GENERIC)
        if updated_hash is not None:
            user.hashed_password = updated_hash
        credential = self.db.query(AdminCredential).filter_by(user_id=user.id).with_for_update().first()
        enrolling = credential is None or credential.totp_enabled_at is None
        result: dict = {"step": "enroll" if enrolling else "code"}
        if enrolling:
            # A new secret each time until the first code confirms it.
            secret = totp.new_secret()
            if credential is None:
                credential = AdminCredential(user_id=user.id, totp_secret_encrypted=_seal(secret))
                self.db.add(credential)
            else:
                credential.totp_secret_encrypted = _seal(secret)
            result.update(secret=secret, otpauth_uri=totp.provisioning_uri(secret, user.email, settings.ADMIN_TOTP_ISSUER))
        self.db.commit()
        result["challenge"] = _create_token(str(user.id), timedelta(minutes=CHALLENGE_MINUTES), "admin_challenge",
                                            {"pv": password_version(user.hashed_password)})
        return result, user

    def verify(self, *, challenge: str, code: str, user_agent: str | None, ip_address: str | None) -> tuple[dict, User | None]:
        try:
            payload = decode_token(challenge, expected_type="admin_challenge")
        except (JWTError, ValueError):
            raise UnauthorizedError("Your sign-in step expired. Start again.")
        user = self.db.get(User, uuid.UUID(payload["sub"]))
        credential = (self.db.query(AdminCredential).filter_by(user_id=user.id).with_for_update()
                      .populate_existing().first() if user else None)
        if (user is None or credential is None or user.role != "admin" or not user.is_active
                or not admin_email_allowed(user.email) or payload.get("pv") != password_version(user.hashed_password)):
            raise UnauthorizedError(GENERIC)
        counter = totp.verify(_open(credential.totp_secret_encrypted), code, last_counter=credential.totp_last_counter)
        if counter is None:
            raise UnauthorizedError(GENERIC)
        credential.totp_last_counter = counter  # the same code can't be used twice
        if credential.totp_enabled_at is None:
            credential.totp_enabled_at = datetime.utcnow()
        refresh = create_refresh_token(str(user.id))
        from app.services.auth_service import AuthService
        self.db.add(RefreshSession(user_id=user.id, refresh_token_hash=AuthService._hash_token(refresh),
                                   user_agent=user_agent, ip_address=ip_address, mfa_verified=True,
                                   expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)))
        self.db.commit()
        access = create_access_token(str(user.id), user.role,
                                     {"password_version": password_version(user.hashed_password), "mfa": True,
                                      "mfa_cred": str(credential.id)})
        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}, user


def _step_up_required(message: str = "Enter a code from your authenticator app to approve or reject.") -> ForbiddenError:
    return ForbiddenError(message, error_code="step_up_required")


class AdminStepUpService:
    """Re-check the authenticator before an admin approves or rejects a verification.

    One fresh code opens a STEP_UP_MINUTES window (a signed pass bound to this admin and their
    current authenticator), so several decisions in a row don't each wait for a new code. The
    code is replay-protected the same way as at sign-in."""

    def __init__(self, db: Session):
        self.db = db

    def open_window(self, *, user: User, code: str) -> dict:
        credential = (self.db.query(AdminCredential).filter_by(user_id=user.id).with_for_update()
                      .populate_existing().first())
        if credential is None or credential.totp_enabled_at is None:
            raise ForbiddenError("Set up your authenticator app (sign out and back in) before reviewing.",
                                 error_code="step_up_unavailable")
        counter = totp.verify(_open(credential.totp_secret_encrypted), code, last_counter=credential.totp_last_counter)
        if counter is None:
            self.db.rollback()
            raise ForbiddenError("That code didn't work. Enter the newest code from your authenticator app.",
                                 error_code="step_up_failed")
        credential.totp_last_counter = counter  # the same code can't be used twice
        self.db.commit()
        expires = datetime.utcnow() + timedelta(minutes=STEP_UP_MINUTES)
        token = _create_token(str(user.id), timedelta(minutes=STEP_UP_MINUTES), "admin_step_up", {"cred": str(credential.id)})
        return {"step_up_token": token, "expires_at": expires.isoformat() + "Z", "minutes": STEP_UP_MINUTES}

    def require(self, *, user: User, token: str | None) -> None:
        if not token:
            raise _step_up_required()
        try:
            payload = decode_token(token, expected_type="admin_step_up")
        except (JWTError, ValueError):
            raise _step_up_required("Your review window has ended. Enter a new authenticator code.")
        if payload.get("sub") != str(user.id) or payload.get("cred") != active_credential_id(self.db, user.id):
            raise _step_up_required()
