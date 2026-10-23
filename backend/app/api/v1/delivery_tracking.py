"""Authorized courier GPS ingestion for assigned active deliveries."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import Role, require_roles
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.user import User
from app.schemas.tracking import GPSPingRequest, TrackingResponse
from app.services.tracking_service import TrackingService

router = APIRouter(prefix="/delivery-tracking", tags=["Delivery Tracking"])

ACTIVE_DELIVERY_STATUSES = {"picked_up", "in_transit", "out_for_delivery"}


@router.post("/{delivery_id}/pings", response_model=TrackingResponse)
def record_delivery_ping(
    delivery_id: uuid.UUID,
    payload: GPSPingRequest,
    current_user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    # Ownership is proven from the database, not a caller-provided rider ID.
    delivery = (db.query(Delivery)
                .join(DeliveryPartner, Delivery.delivery_partner_id == DeliveryPartner.id)
                .filter(Delivery.id == delivery_id, DeliveryPartner.user_id == current_user.id,
                        DeliveryPartner.is_verified.is_(True),
                        Delivery.status.in_(ACTIVE_DELIVERY_STATUSES))
                .first())
    if delivery is None:
        raise NotFoundError("Assigned active delivery not found.")
    return TrackingService(db).record_gps_ping(
        delivery_id, latitude=payload.latitude, longitude=payload.longitude,
        eta_minutes=payload.eta_minutes, delivery_status=delivery.status,
    )
