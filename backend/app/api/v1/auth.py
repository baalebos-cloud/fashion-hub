"""
/api/v1/auth

Rate limiting: apply a strict limiter (see settings.RATE_LIMIT_AUTH) to
/login, /forgot-password, and /reset-password specifically in main.py's
limiter configuration, since these are classic brute-force/enumeration
targets.
"""
from fastapi import APIRouter, Depends, Request
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
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=201)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def sign_up(payload: SignUpRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.sign_up(
        email=payload.email,
        phone_number=payload.phone_number,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
        referral_code=payload.referral_code,
    )
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def log_in(payload: LogInRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    result = service.log_in(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(access_token=result["access_token"], refresh_token=result["refresh_token"])


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh_access_token(payload.refresh_token)


@router.post("/logout", status_code=204)
def log_out(payload: RefreshRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.log_out(payload.refresh_token)
    return None


@router.post("/verify-email", status_code=204)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.verify_email(payload.token)
    return None


@router.post("/forgot-password", status_code=202)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.request_password_reset(payload.email)
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=204)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.reset_password(token=payload.token, new_password=payload.new_password)
    return None
