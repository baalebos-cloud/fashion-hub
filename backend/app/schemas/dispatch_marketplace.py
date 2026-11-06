import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MyOffer(BaseModel):
    id: uuid.UUID
    amount: float
    status: str
    eta_to_pickup_minutes: int
    expires_at: datetime


class RouteSummary(BaseModel):
    """A road route from a routing provider, or the labelled straight-line estimate."""
    distance_km: float | None
    duration_minutes: int | None
    source: str
    verified: bool
    traffic_aware: bool = False
    computed_at: str | None = None
    cached: bool = False
    fallback_reason: str | None = None


class DispatchJob(BaseModel):
    """What a rider sees before claiming: no exact addresses, contacts or names."""
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    suggested_fare: float
    currency: str
    offer_min: float
    offer_max: float
    approx_road_km: float | None
    route: RouteSummary | None = None
    pickup_area: str | None
    dropoff_area: str | None
    posted_at: datetime
    my_offer: MyOffer | None


class MakeOfferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    eta_to_pickup_minutes: int = Field(ge=1, le=120)


class OfferResponse(BaseModel):
    id: uuid.UUID
    amount: float
    eta_to_pickup_minutes: int
    status: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class RiderCard(BaseModel):
    first_name: str
    is_verified: bool
    rating: float
    vehicle_type: str | None
    completed_deliveries: int
    photo_url: str | None


class SellerOffer(BaseModel):
    id: uuid.UUID
    amount: float
    eta_to_pickup_minutes: int
    expires_at: datetime
    rider: RiderCard


class SellerDispatchRequest(BaseModel):
    id: uuid.UUID
    status: str
    suggested_fare: float
    approx_road_km: float | None
    currency: str
    route: RouteSummary | None = None


class SellerDispatchView(BaseModel):
    request: SellerDispatchRequest | None
    offers: list[SellerOffer]


class JourneyMilestone(BaseModel):
    key: str
    label: str
    at: datetime | None
    state: Literal["done", "current", "upcoming"]


class JourneyLive(BaseModel):
    eta_minutes: int | None
    distance_remaining_km: float | None
    basis: Literal["live_gps_estimate", "road_route"]
    route_source: str | None = None
    traffic_aware: bool = False
    route_computed_at: str | None = None
    updated_at: str | None


class MaterialsLeg(BaseModel):
    """Vendor -> tailor leg feeding a customer order. No prices, addresses or contacts."""
    order_id: uuid.UUID
    vendor_name: str
    status: str
    label: str
    done: bool
    updated_at: datetime | None = None


class DeliveryJourney(BaseModel):
    order_id: uuid.UUID
    tracking_number: str
    status: str
    delivery_status: str | None
    milestones: list[JourneyMilestone]
    live: JourneyLive | None
    materials_legs: list[MaterialsLeg] = []


class ReservedJob(BaseModel):
    """A job auto-offered exclusively to this rider until expires_at."""
    id: uuid.UUID
    expires_at: datetime
    attempt: int
    job: DispatchJob
