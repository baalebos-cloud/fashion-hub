"""Authenticated, read-only sandbox Saga audit status.

No public API accepts an untrusted provider_confirmed=True flag.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.order import Order
from app.models.user import User
from app.services.saga.orchestrator import SandboxSagaService

router = APIRouter(prefix="/saga", tags=["Sandbox Order Saga"])


@router.get("/orders/{order_id}")
def get_saga_status(order_id: UUID, current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise NotFoundError("Order not found.")
    if current_user.role != "admin" and str(current_user.id) not in {
        str(order.buyer_user_id), str(order.seller_user_id),
    }:
        raise ForbiddenError("Not authorized to view this order.")
    state = SandboxSagaService(db).state(order_id)
    return {
        "order_id": str(order_id),
        "state": state,
        "simulation": True,
        "provider_funds_verified": False,
        "receipt": None,
    }
