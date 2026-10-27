"""Courier onboarding, availability and admin-only verification."""
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Role, require_roles
from app.models.audit_log import AuditLog
from app.models.delivery_partner import DeliveryPartner
from app.models.user import User
from app.schemas.delivery_partner import DeliveryPartnerResponse, SetAvailabilityRequest
from app.services.delivery_partner_service import DeliveryPartnerService

router = APIRouter(prefix="/delivery-partners", tags=["Delivery Partners"])


class CourierVehicle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_type: Literal["bike", "car", "van", "foot"]


@router.get("/me", response_model=DeliveryPartnerResponse)
def me(user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
       db: Session = Depends(get_db)):
    return DeliveryPartnerService(db).get_or_create(user)


@router.put("/me", response_model=DeliveryPartnerResponse)
def save_profile(payload: CourierVehicle,
                 user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
                 db: Session = Depends(get_db)):
    return DeliveryPartnerService(db).save_vehicle(actor=user, vehicle_type=payload.vehicle_type)


@router.put("/me/availability", response_model=DeliveryPartnerResponse)
def availability(payload: SetAvailabilityRequest,
                 user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
                 db: Session = Depends(get_db)):
    partner = DeliveryPartnerService(db).get_or_create(user)
    return DeliveryPartnerService(db).set_availability(
        partner.id, is_available=payload.is_available,
    )


@router.get("/admin/pending", response_model=list[DeliveryPartnerResponse])
def unverified(user: User = Depends(require_roles(Role.ADMIN)),
               db: Session = Depends(get_db)):
    return (db.query(DeliveryPartner).filter(DeliveryPartner.is_verified.is_(False))
            .order_by(DeliveryPartner.created_at, DeliveryPartner.id).limit(100).all())


@router.post("/{partner_id}/verify", response_model=DeliveryPartnerResponse)
def verify(partner_id: UUID, user: User = Depends(require_roles(Role.ADMIN)),
           db: Session = Depends(get_db)):
    partner = (db.query(DeliveryPartner).filter(DeliveryPartner.id == partner_id)
               .with_for_update().populate_existing().first())
    if partner is None:
        raise NotFoundError("Courier profile not found.")
    if not partner.vehicle_type:
        raise ConflictError("Courier must select a vehicle before verification.")
    if not partner.is_verified:
        partner.is_verified = True
        db.add(AuditLog(actor_user_id=user.id, action="courier.verified",
                        resource_type="delivery_partner", resource_id=partner.id))
        db.commit()
        db.refresh(partner)
    return partner
