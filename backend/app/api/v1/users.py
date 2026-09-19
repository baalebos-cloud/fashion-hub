"""
/users

Profile management shared across roles. GET/PATCH /users/me is the
"current user" endpoint the frontend calls on every app boot (see
frontend hooks/use-auth.ts -> lib/auth/session.ts::restoreSession).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import CurrentUserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=CurrentUserResponse)
def update_me(payload: UserUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)
    return service.update_profile(current_user.id, **payload.model_dump(exclude_unset=True))
