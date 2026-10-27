"""Courier-owned profile/availability and explicit administrator verification."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.user import User


class DeliveryPartnerService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, actor: User):
        self.db.query(User).filter(User.id == actor.id).with_for_update().one()
        partner = self.db.query(DeliveryPartner).filter_by(user_id=actor.id).first()
        if partner is None:
            partner = DeliveryPartner(user_id=actor.id, is_verified=False, is_available=False)
            self.db.add(partner)
            self.db.commit()
            self.db.refresh(partner)
        return partner

    def save_vehicle(self, *, actor: User, vehicle_type: str):
        partner = self.get_or_create(actor)
        if partner.vehicle_type != vehicle_type:
            partner.vehicle_type = vehicle_type
            # A changed vehicle requires an administrator to verify again.
            partner.is_verified = False
            partner.is_available = False
            self.db.commit()
            self.db.refresh(partner)
        return partner

    def set_availability(self, delivery_partner_id, *, is_available: bool):
        partner = (self.db.query(DeliveryPartner)
                   .filter(DeliveryPartner.id == delivery_partner_id)
                   .with_for_update().populate_existing().first())
        if partner is None:
            raise NotFoundError("Courier profile not found.")
        if is_available and not partner.is_verified:
            raise ConflictError("Administrator verification is required before accepting deliveries.")
        if is_available and (self.db.query(Delivery.id)
                             .filter(Delivery.delivery_partner_id == partner.id,
                                     Delivery.status.in_({"assigned", "in_transit"})).first()):
            raise ConflictError("An active delivery must be completed before going available.")
        partner.is_available = is_available
        self.db.commit()
        self.db.refresh(partner)
        return partner
