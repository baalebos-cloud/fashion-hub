"""Authorized internal courier delivery lifecycle."""
import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.schemas.dispatch_marketplace import DeliveryJourney
from app.schemas.delivery import DeliveryResponse, DeliveryTrackingResponse, MarkDeliveredRequest, MarkPickedUpRequest
from app.schemas.dispatch_trip import DeliveryTripResponse
from app.schemas.delivery_position import RiderDeviceStateInput, RiderPositionInput, RiderPositionResponse, RiderSharingSession
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


@router.get("/orders/{order_id}/tracking", response_model=DeliveryTrackingResponse | None)
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
    # The current run: a delivery released or reassigned by dispatch is never shown as "your rider".
    delivery = (db.query(Delivery).filter(Delivery.order_id == order.id, Delivery.status != "cancelled")
                .order_by(Delivery.created_at.desc()).first())
    if delivery is None:
        return None
    partner = db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery.delivery_partner_id else None
    rider = db.get(User, partner.user_id) if partner else None
    completed = None
    if partner:
        from sqlalchemy import func
        completed = int(db.query(func.count(Delivery.id)).filter(
            Delivery.delivery_partner_id == partner.id, Delivery.status == "delivered").scalar() or 0)
    return {
        "id": delivery.id, "order_id": delivery.order_id,
        "status": delivery.status, "delivery_fee": delivery.delivery_fee,
        "package_count": delivery.package_count,
        "rider_name": rider.full_name if rider else None,
        "rider_verified": bool(partner.is_verified) if partner else None,
        "rider_rating": float(partner.average_rating or 0) if partner else None,
        "rider_vehicle_type": partner.vehicle_type if partner else None,
        "rider_completed_deliveries": completed,
        "rider_photo_url": rider.profile_photo_url if rider else None,
    }


@router.get("/orders/{order_id}/journey", response_model=DeliveryJourney)
def order_journey(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logistics-style milestones with times, plus an approximate live ETA while in transit."""
    from app.services.dispatch_marketplace_service import DispatchMarketplaceService
    return DispatchMarketplaceService(db).journey(order_id=order_id, actor=user)


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
    payload: Optional[MarkPickedUpRequest] = Body(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """Rider confirms collection with the seller's pickup code and the number of packages.
    Send an Idempotency-Key so a retried request after a dropped connection is answered safely."""
    payload = payload or MarkPickedUpRequest()
    return InternalCourierService(db).transition(
        delivery_id=delivery_id, actor=user, action="picked-up", pickup_code_input=payload.pickup_code,
        package_count=payload.package_count, idempotency_key=idempotency_key)


@router.post("/{delivery_id}/delivered", response_model=DeliveryResponse)
def mark_delivered(
    delivery_id: uuid.UUID,
    payload: MarkDeliveredRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).transition(
        delivery_id=delivery_id, actor=user, action="delivered",
        handover_code_input=payload.handover_code, idempotency_key=idempotency_key)


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
    """Return the current one-time code only to the delivery's customer after pickup; never to
    the rider. A lapsed code is replaced automatically."""
    return InternalCourierService(db).customer_handover_code(delivery_id=delivery_id, actor=user)


@router.post("/{delivery_id}/handover-code/rotate")
def rotate_handover_code(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Customer replaces their code (e.g. they read it to the wrong person). The old one stops working."""
    return InternalCourierService(db).customer_handover_code(delivery_id=delivery_id, actor=user, rotate=True)


@router.get("/{delivery_id}/pickup-code")
def seller_pickup_code(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The seller's code to give the rider at collection. Never shown to the rider or buyer."""
    return InternalCourierService(db).seller_pickup_code(delivery_id=delivery_id, actor=user)


@router.post("/{delivery_id}/pickup-code/rotate")
def rotate_pickup_code(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).seller_pickup_code(delivery_id=delivery_id, actor=user, rotate=True)


@router.post("/{delivery_id}/position/start", response_model=RiderSharingSession)
def begin_rider_position(
    delivery_id: uuid.UUID,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """Consent is given by the assigned rider's deliberate Start action."""
    return InternalCourierService(db).begin_position(delivery_id=delivery_id, actor=user)


@router.post("/{delivery_id}/position", response_model=RiderPositionResponse)
def share_rider_position(
    delivery_id: uuid.UUID,
    payload: RiderPositionInput,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """Explicit, temporary GPS sharing by the rider assigned to an active delivery."""
    return InternalCourierService(db).report_position(
        delivery_id=delivery_id, actor=user, **payload.model_dump(),
    )


@router.post("/{delivery_id}/position/state", status_code=204)
def report_rider_device_state(
    delivery_id: uuid.UUID,
    payload: RiderDeviceStateInput,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """The rider's phone reports why it has no location (permission denied, no signal, paused)."""
    InternalCourierService(db).report_device_state(delivery_id=delivery_id, actor=user, **payload.model_dump())


@router.get("/{delivery_id}/position", response_model=RiderPositionResponse | None)
def authorized_rider_position(
    delivery_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Customer, seller and assigned courier can inspect unexpired rider GPS."""
    return InternalCourierService(db).current_position(delivery_id=delivery_id, actor=user)


@router.delete("/{delivery_id}/position", status_code=204)
def stop_rider_position(
    delivery_id: uuid.UUID,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """End GPS sharing immediately without waiting for the 90-second expiry."""
    InternalCourierService(db).stop_position(delivery_id=delivery_id, actor=user)
