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
from app.schemas.delivery import DeliveryResponse
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
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).transition(delivery_id=delivery_id, actor=user, action="delivered")
