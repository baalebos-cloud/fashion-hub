"""
/delivery-requests

Create/accept/reject delivery requests. See order lifecycle READY_FOR_DELIVERY/READY_FOR_PICKUP triggers.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/delivery-requests", tags=["Delivery Requests"])


@router.get("/health-check")
def module_placeholder():
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Delivery Requests."""
    return {"module": "Delivery Requests", "status": "not yet implemented"}
