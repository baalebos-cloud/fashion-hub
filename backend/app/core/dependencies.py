"""
Shared FastAPI dependencies used across route modules.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """For endpoints that behave differently for logged-in vs anonymous users
    (e.g. public tailor profile pages) without requiring authentication."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


class PaginationParams:
    """Common pagination/sorting query params for list endpoints."""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
        sort_by: Optional[str] = Query(None),
        sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.offset = (page - 1) * page_size


def get_request_id(x_request_id: Optional[str] = None) -> str:
    """Populated by middleware; exposed as a dependency for handlers/services
    that want to attach it to audit logs or provider calls."""
    import uuid
    return x_request_id or str(uuid.uuid4())
