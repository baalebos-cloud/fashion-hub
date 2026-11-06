"""Role-authorized, rider-ready pickup/drop-off contract."""
import uuid

from pydantic import BaseModel, Field


class DispatchWaypoint(BaseModel):
    address: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    lga: str | None = None
    landmark: str | None = None
    nearest_bus_stop: str | None = None
    delivery_instructions: str | None = None
    contact_name: str | None = None
    # Real numbers are never returned; parties call each other via POST /calls.
    can_call: bool = False


class DeliveryTripResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    delivery_fee: float
    pickup: DispatchWaypoint
    dropoff: DispatchWaypoint
    straight_line_km: float | None = None
    distance_source: str = "haversine"
    # Pickup -> drop-off road route (with the line to draw), only for parties to the order.
    route: dict | None = None
    # Haversine is a distance bound, not actual driving distance or ETA.
