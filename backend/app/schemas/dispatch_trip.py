"""Role-authorized, rider-ready pickup/drop-off contract."""
import uuid

from pydantic import BaseModel, Field


class DispatchWaypoint(BaseModel):
    address: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    contact_name: str | None = None
    contact_phone: str | None = None


class DeliveryTripResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    delivery_fee: float
    pickup: DispatchWaypoint
    dropoff: DispatchWaypoint
    straight_line_km: float | None = None
    distance_source: str = "haversine"
    # Haversine is a distance bound, not actual driving distance or ETA.
