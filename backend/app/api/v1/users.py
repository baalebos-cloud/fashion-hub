"""
/users

Profile management shared across roles. GET/PATCH /users/me is the
"current user" endpoint the frontend calls on every app boot (see
frontend hooks/use-auth.ts -> lib/auth/session.ts::restoreSession).
"""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import CurrentUserResponse, UserUpdateRequest
from app.services.account_deletion_service import AccountDeletionService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=CurrentUserResponse)
def update_me(payload: UserUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)
    return service.update_profile(current_user.id, **payload.model_dump(exclude_unset=True))


# ---- Deleting your own account -------------------------------------------------------------
class AccountDeletionStatus(BaseModel):
    can_delete: bool
    blockers: list[str]


class AccountDeletionRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.get("/me/deletion", response_model=AccountDeletionStatus)
def deletion_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Can this account be deleted right now, and if not, what has to finish first."""
    blockers = AccountDeletionService(db).blockers(current_user)
    return {"can_delete": not blockers, "blockers": blockers}


@router.delete("/me", status_code=204)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def delete_me(payload: AccountDeletionRequest, request: Request, current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """Delete your account (needs your password). See services/account_deletion_service.py for what
    is erased and what is kept."""
    AccountDeletionService(db).delete(current_user, password=payload.password)
    return Response(status_code=204)
