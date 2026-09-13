"""Delivery status management and external-provider synchronization."""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.timezone import utcnow


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db

    def mark_picked_up(self, delivery_id):
        from app.models.delivery import Delivery

        delivery = self.db.get(Delivery, delivery_id)
        if not delivery:
            raise NotFoundError("Delivery not found.")
        delivery.status = "picked_up"
        delivery.picked_up_at = utcnow()
        self.db.commit()
        return delivery

    def mark_delivered(self, delivery_id, *, proof_of_delivery_url: str | None = None):
        from app.models.delivery import Delivery

        delivery = self.db.get(Delivery, delivery_id)
        if not delivery:
            raise NotFoundError("Delivery not found.")
        delivery.status = "delivered"
        delivery.delivered_at = utcnow()
        if proof_of_delivery_url:
            delivery.proof_of_delivery_url = proof_of_delivery_url
        self.db.commit()
        return delivery

    def sync_status_from_provider(self, delivery_id: str):
        """For non-internal providers only; internal deliveries are updated
        directly by delivery-partner app actions."""
        from app.models.delivery import Delivery

        delivery = self.db.get(Delivery, delivery_id)
        if not delivery or delivery.provider == "internal":
            return
        from app.integrations.delivery import get_delivery_provider
        provider = get_delivery_provider()
        status_result = provider.get_delivery_status(delivery.provider_tracking_reference)
        delivery.status = status_result.status
        self.db.commit()
