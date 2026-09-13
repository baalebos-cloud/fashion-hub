"""Delivery partner profile management, availability toggling, and
verification-badge status derived from KYC."""
from sqlalchemy.orm import Session


class DeliveryPartnerService:
    def __init__(self, db: Session):
        self.db = db

    def set_availability(self, delivery_partner_id, *, is_available: bool):
        from app.models.delivery_partner import DeliveryPartner
        from app.core.exceptions import NotFoundError

        partner = self.db.get(DeliveryPartner, delivery_partner_id)
        if not partner:
            raise NotFoundError("Delivery partner not found.")
        partner.is_available = is_available
        self.db.commit()
        return partner
