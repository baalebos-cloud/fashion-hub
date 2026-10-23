"""Seller-created delivery requests, listed and claimed by verified couriers."""
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.delivery import DeliveryResponse
from app.schemas.delivery_request import DeliveryRequestResponse
from app.services.internal_courier_service import InternalCourierService

router = APIRouter(prefix="/delivery-requests", tags=["Delivery Requests"])


@router.post("/orders/{order_id}", response_model=DeliveryRequestResponse, status_code=201)
def request_delivery(
    order_id: uuid.UUID,
    user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).request(order_id=order_id, actor=user)


@router.get("/available", response_model=list[DeliveryRequestResponse])
def available_deliveries(
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    # Summary only; no destination coordinates or customer identity are
    # exposed to couriers before they accept an assignment.
    return InternalCourierService(db).list_available(actor=user, limit=limit)


@router.post("/{request_id}/accept", response_model=DeliveryResponse)
def accept_delivery(
    request_id: uuid.UUID,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).accept(request_id=request_id, actor=user)
