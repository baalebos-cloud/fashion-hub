"""
Role-based access control (RBAC) primitives.

Two layers of authorization are used across the app:

1. Role-level: "only tailors can access this endpoint" -> `require_roles`.
2. Resource-level (ownership): "a tailor can only modify THEIR OWN order"
   -> checked in the service layer via functions like `assert_owns_order`,
   never trusted from client-supplied IDs alone.

Keeping both layers explicit prevents the common bug class of "role check
passed, but any tailor could edit any other tailor's data".
"""
from enum import Enum
from typing import Iterable

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User


class Role(str, Enum):
    CUSTOMER = "customer"
    TAILOR = "tailor"
    DESIGNER = "designer"
    VENDOR = "vendor"
    DELIVERY_PARTNER = "delivery_partner"
    ADMIN = "admin"


def require_roles(*allowed_roles: Role):
    """
    FastAPI dependency factory.

    Usage:
        @router.post("/orders/{id}/accept")
        def accept_order(..., user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER))):
            ...
    """
    allowed_values = {r.value for r in allowed_roles}

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _checker


def assert_is_owner_or_admin(current_user: User, owner_user_id) -> None:
    """Generic ownership guard used by services before mutating a resource."""
    if current_user.role != Role.ADMIN.value and str(current_user.id) != str(owner_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )


def assert_role_in(current_user: User, allowed: Iterable[Role]) -> None:
    if current_user.role not in {r.value for r in allowed}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
