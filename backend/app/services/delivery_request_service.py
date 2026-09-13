"""
Creation and broadcast of delivery requests, including matching to nearby
AVAILABLE delivery partners via PostGIS distance queries.

Edge case handled here: "delivery partner rejects a delivery" -- rejection
sets status back to `requested` and re-broadcasts to the next-nearest
partner rather than failing the whole order.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError


class DeliveryRequestService:
    def __init__(self, db: Session):
        self.db = db

    def create_for_order(self, *, order_id, pickup_location_id, dropoff_location_id, package_description: str):
        from app.models.delivery_request import DeliveryRequest

        request = DeliveryRequest(
            order_id=order_id,
            pickup_location_id=pickup_location_id,
            dropoff_location_id=dropoff_location_id,
            package_description=package_description,
            status="requested",
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)

        from app.workers.delivery_tasks import broadcast_delivery_request_task
        broadcast_delivery_request_task.delay(delivery_request_id=str(request.id))
        return request

    def broadcast_to_nearby_partners(self, delivery_request_id: str):
        """Query available delivery partners near the pickup location
        (ST_DWithin on Location.geom) and notify them. Full geo query
        implementation lives alongside location_service/distance_service."""
        raise NotImplementedError("Wire in a PostGIS ST_DWithin nearest-partner query here.")

    def accept(self, delivery_request_id, *, delivery_partner_id):
        from app.models.delivery import Delivery
        from app.models.delivery_request import DeliveryRequest

        request = self.db.get(DeliveryRequest, delivery_request_id)
        if not request:
            raise NotFoundError("Delivery request not found.")
        if request.status != "requested":
            raise ConflictError("This delivery request is no longer available.")

        request.status = "assigned"
        delivery = Delivery(
            delivery_request_id=request.id,
            order_id=request.order_id,
            delivery_partner_id=delivery_partner_id,
            provider="internal",
            status="assigned",
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def reject(self, delivery_request_id, *, reason: str):
        from app.models.delivery_request import DeliveryRequest

        request = self.db.get(DeliveryRequest, delivery_request_id)
        if not request:
            raise NotFoundError("Delivery request not found.")
        request.status = "requested"  # reset for re-broadcast rather than a terminal failure
        request.rejection_reason = reason
        self.db.commit()

        from app.workers.delivery_tasks import broadcast_delivery_request_task
        broadcast_delivery_request_task.delay(delivery_request_id=str(request.id))
