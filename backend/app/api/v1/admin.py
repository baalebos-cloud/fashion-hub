"""
/admin

Admin-only operations: KYC/KYB review, dispute resolution, audit log browsing, platform configuration.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.services.commerce_dashboard_service import load_commerce_summary

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health-check")
def module_placeholder():
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Admin."""
    return {"module": "Admin", "status": "not yet implemented"}


@router.get("/commerce-summary")
def commerce_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    """Admin-only real payment ledger aggregates; no customer records."""
    return load_commerce_summary(db)
