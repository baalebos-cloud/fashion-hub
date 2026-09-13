"""
/delivery-tracking

Live GPS ping ingestion (delivery partner app) and read endpoints (customer/tailor tracking UI).

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/delivery-tracking", tags=["Delivery Tracking"])


@router.get("/health-check")
def module_placeholder():
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Delivery Tracking."""
    return {"module": "Delivery Tracking", "status": "not yet implemented"}
