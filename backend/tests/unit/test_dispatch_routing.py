"""Sage-inspired route validation, with no invented road ETA or fees."""
import pytest
from app.core.exceptions import ValidationAppError
from app.services.dispatch_routing import estimate_straight_line_km, validate_point


def test_valid_nigerian_coordinates_produce_only_a_straight_line_estimate():
    origin = validate_point(7.64037, 5.22102)
    destination = validate_point(7.7, 5.25)
    estimate = estimate_straight_line_km(origin, destination)
    assert estimate is not None and 0 < estimate < 20


def test_missing_coordinates_do_not_fabricate_distance():
    assert validate_point(None, None) is None
    assert estimate_straight_line_km(None, validate_point(7.6, 5.2)) is None


@pytest.mark.parametrize("lat,lng", [(91, 5), (7, 190), (float("nan"), 5), (0, float("inf"))])
def test_invalid_coordinates_are_rejected(lat, lng):
    with pytest.raises(ValidationAppError):
        validate_point(lat, lng)
