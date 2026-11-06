"""
/api/v1/auth

Rate limiting: apply a strict limiter (see settings.RATE_LIMIT_AUTH) to
/login, /forgot-password, and /reset-password specifically in main.py's
limiter configuration, since these are classic brute-force/enumeration
targets.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    LogInRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignUpRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.core.client_info import client_ip
from app.core.exceptions import AppError
from app.services import activity_service
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=201)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def sign_up(payload: SignUpRequest, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.sign_up(
        email=payload.email,
        phone_number=payload.phone_number,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
        referral_code=payload.referral_code,
    )
    activity_service.record(request, "sign_up", user=user, status_code=201)
    _send_now(background, user.id)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def log_in(payload: LogInRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        result = service.log_in(
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip(request),
        )
    except AppError as exc:
        db.rollback()
        activity_service.record(request, "sign_in_failed", status_code=getattr(exc, "status_code", 401),
                                details={"email": str(payload.email).lower()[:255]})
        raise
    activity_service.record(request, "sign_in", user=result.get("user"), status_code=200)
    return TokenResponse(access_token=result["access_token"], refresh_token=result["refresh_token"])


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh_access_token(payload.refresh_token)


@router.post("/logout", status_code=204)
def log_out(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.log_out(payload.refresh_token)
    activity_service.record(request, "sign_out", status_code=204)
    return None


@router.post("/verify-email", status_code=204)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.verify_email(payload.token)
    return None


@router.post("/forgot-password", status_code=202)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def forgot_password(payload: ForgotPasswordRequest, request: Request, background: BackgroundTasks,
                    db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.request_password_reset(payload.email)
    if user is not None:
        _send_now(background, user.id)  # this person's email, not whatever is oldest in the queue
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/resend-verification", status_code=202)
@limiter.limit("3/minute")
def resend_verification(payload: ForgotPasswordRequest, request: Request, background: BackgroundTasks,
                        db: Session = Depends(get_db)):
    """Send a new email-confirmation link. Same answer whether or not the account exists."""
    user = AuthService(db).resend_verification(payload.email)
    if user is not None:
        _send_now(background, user.id)
    return {"message": "If that email has an unconfirmed Tailora account, a new confirmation link is on its way."}


def _send_now(background: BackgroundTasks, user_id=None) -> None:
    """Deliver queued auth email right after the response, without waiting for a worker.
    The Celery beat drain retries anything the provider refused."""
    if settings.APP_ENV == "test":
        return
    from app.services.auth_email_outbox_service import send_in_background
    background.add_task(send_in_background, user_id)


@router.post("/reset-password", status_code=204)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.reset_password(token=payload.token, new_password=payload.new_password)
    activity_service.record(request, "password_reset", user=user, status_code=204)
    return None


# ---- Admin two-step sign-in (password, then authenticator app) -----------------------------
class AdminLogInRequest(LogInRequest):
    pass


class AdminVerifyRequest(BaseModel):
    challenge: str = Field(min_length=20, max_length=2048)
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


@router.post("/admin/login")
@limiter.limit("5/minute")
def admin_log_in(payload: AdminLogInRequest, request: Request, db: Session = Depends(get_db)):
    """Step 1. Returns a short-lived challenge, plus the authenticator setup key on first use."""
    from app.services.admin_auth_service import AdminAuthService
    try:
        result, user = AdminAuthService(db).start(email=str(payload.email), password=payload.password)
    except AppError as exc:
        db.rollback()
        activity_service.record(request, "admin_sign_in_failed", status_code=getattr(exc, "status_code", 401),
                                details={"email": str(payload.email).lower()[:255], "step": "password"})
        raise
    return result


@router.post("/admin/verify", response_model=TokenResponse)
@limiter.limit("5/minute")
def admin_verify(payload: AdminVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Step 2. A current authenticator code completes the admin sign-in."""
    from app.services.admin_auth_service import AdminAuthService
    try:
        tokens, user = AdminAuthService(db).verify(challenge=payload.challenge, code=payload.code,
                                                   user_agent=request.headers.get("user-agent"),
                                                   ip_address=client_ip(request))
    except AppError as exc:
        db.rollback()
        activity_service.record(request, "admin_sign_in_failed", status_code=getattr(exc, "status_code", 401),
                                details={"step": "code"})
        raise
    activity_service.record(request, "admin_sign_in", user=user, status_code=200)
    return TokenResponse(access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])
