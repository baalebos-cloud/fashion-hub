"""Authorized internal courier delivery lifecycle."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.schemas.delivery import DeliveryResponse, MarkDeliveredRequest
from app.services.internal_courier_service import InternalCourierService

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


@router.get("/mine/active", response_model=list[DeliveryResponse])
def my_active_deliveries(
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """Only assigned courier sees their own current delivery runs."""
    return (db.query(Delivery).join(DeliveryPartner, Delivery.delivery_partner_id == DeliveryPartner.id)
            .filter(DeliveryPartner.user_id == user.id,
                    Delivery.status.in_(["assigned", "picked_up", "in_transit", "out_for_delivery"]))
            .order_by(Delivery.created_at.desc()).limit(50).all())


@router.get("/orders/{order_id}/tracking", response_model=DeliveryResponse | None)
def customer_order_delivery(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Order-scoped tracking, never a public lookup by arbitrary order ID."""
    from app.models.order import Order
    from app.core.exceptions import NotFoundError
    order = db.get(Order, order_id)
    if not order or (str(user.id) not in {str(order.buyer_user_id), str(order.seller_user_id)}
                     and user.role != "admin"):
        raise NotFoundError("Delivery not found.")
    return db.query(Delivery).filter(Delivery.order_id == order.id).order_by(
        Delivery.created_at.desc()).first()


@router.get("/{delivery_id}", response_model=DeliveryResponse)
def delivery_details(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).get(delivery_id=delivery_id, actor=user)


@router.post("/{delivery_id}/picked-up", response_model=DeliveryResponse)
def mark_picked_up(
    delivery_id: uuid.UUID,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).transition(delivery_id=delivery_id, actor=user, action="picked-up")


@router.post("/{delivery_id}/delivered", response_model=DeliveryResponse)
def mark_delivered(
    delivery_id: uuid.UUID,
    payload: MarkDeliveredRequest,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).transition(delivery_id=delivery_id, actor=user, action="delivered", handover_code_input=payload.handover_code)


@router.get("/{delivery_id}/trip", response_model=DeliveryTripResponse)
def delivery_trip(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only the courier, order owner, seller or admin can see precise trip locations."""
    return InternalCourierService(db).trip(delivery_id=delivery_id, actor=user)

@router.get("/{delivery_id}/handover-code")
def customer_handover_code(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return OTP only to the delivery's customer after pickup; never to the rider."""
    return InternalCourierService(db).customer_handover_code(delivery_id=delivery_id, actor=user)
