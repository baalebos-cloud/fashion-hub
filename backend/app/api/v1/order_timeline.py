"""
/order-timeline

Read-only append-only status history for an order, used by the customer-facing tracker UI.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/order-timeline", tags=["Order Timeline"])


@router.get("/health-check")
def module_placeholder():
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Order Timeline."""
    return {"module": "Order Timeline", "status": "not yet implemented"}
