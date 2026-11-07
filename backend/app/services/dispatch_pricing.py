"""Suggested delivery fares and rough arrival estimates.

Both are labelled as estimates in the product: they use straight-line distance
times a road factor, not a routing engine or live traffic.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings

# Typical urban speeds (km/h) in Nigerian city traffic, by vehicle.
URBAN_SPEED_KMH = {"bike": 22.0, "car": 18.0, "van": 16.0, "foot": 4.5}
OFFER_MIN_RATIO = Decimal("0.8")
OFFER_MAX_RATIO = Decimal("2.0")


def road_km(straight_line_km: float | None) -> float | None:
    if straight_line_km is None:
        return None
    return round(straight_line_km * settings.DISPATCH_ROAD_FACTOR, 1)


def suggested_fare(straight_line_km: float | None) -> Decimal:
    """Base + per-km on approximate road distance, rounded to the nearest ₦50."""
    km = road_km(straight_line_km)
    raw = Decimal(settings.DISPATCH_BASE_FARE) + Decimal(str(km or 0)) * settings.DISPATCH_PER_KM_FARE
    rounded = (raw / 50).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 50
    return max(rounded, Decimal(settings.DISPATCH_MIN_FARE))


def suggested_fare_for_road_km(km: float | None) -> Decimal:
    """Same formula, from a real road distance (only used once the owner switches
    DISPATCH_PRICE_FROM_ROAD_ROUTES on)."""
    raw = Decimal(settings.DISPATCH_BASE_FARE) + Decimal(str(km or 0)) * settings.DISPATCH_PER_KM_FARE
    rounded = (raw / 50).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 50
    return max(rounded, Decimal(settings.DISPATCH_MIN_FARE))


def offer_bounds(suggested: Decimal) -> tuple[Decimal, Decimal]:
    low = (suggested * OFFER_MIN_RATIO / 50).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 50
    high = (suggested * OFFER_MAX_RATIO / 50).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 50
    return low, high


def eta_minutes(straight_line_km: float | None, vehicle_type: str | None) -> int | None:
    km = road_km(straight_line_km)
    if km is None:
        return None
    speed = URBAN_SPEED_KMH.get(vehicle_type or "bike", URBAN_SPEED_KMH["bike"])
    return max(1, round(km / speed * 60))
