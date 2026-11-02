"""Sage-inspired bounded geo validation; straight-line distance is NOT a road ETA."""
from math import asin, cos, isfinite, radians, sin, sqrt

from app.core.exceptions import ValidationAppError


def validate_point(latitude, longitude):
    if latitude is None or longitude is None:
        return None
    lat, lng = float(latitude), float(longitude)
    if not isfinite(lat) or not isfinite(lng) or abs(lat) > 90 or abs(lng) > 180:
        raise ValidationAppError("Invalid dispatch GPS coordinates.")
    return {"latitude": lat, "longitude": lng}


def estimate_straight_line_km(origin, destination):
    """Advisory straight-line lower bound, never a driving fee or promised ETA."""
    if origin is None or destination is None:
        return None
    a, b = radians(origin["latitude"]), radians(destination["latitude"])
    da = b - a
    dl = radians(destination["longitude"] - origin["longitude"])
    h = sin(da / 2) ** 2 + cos(a) * cos(b) * sin(dl / 2) ** 2
    return round(6371.0088 * 2 * asin(min(1.0, sqrt(h))), 3)
