"""Spatial discovery must be bounded and never expose exact GPS coordinates."""
import math
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.services.spatial_discovery import (
    nearby_available_couriers, nearby_material_vendors,
    nearby_professionals, validated_search,
)


@pytest.mark.parametrize("latitude,longitude", [(91, 1), (-91, 1), (0, 181),
                                                    (float("nan"), 1), (1, float("inf"))])
def test_rejects_invalid_coordinates(latitude, longitude):
    with pytest.raises(ValueError):
        validated_search(latitude=latitude, longitude=longitude)


@pytest.mark.parametrize("radius", [0, 99, 50001, float("nan"), math.inf, True])
def test_rejects_unbounded_radius(radius):
    with pytest.raises(ValueError):
        validated_search(latitude=6.52, longitude=3.38, radius_m=radius)


def test_missing_coordinates_without_city_returns_no_discovery():
    db = Mock()
    assert nearby_professionals(db) == []
    assert nearby_available_couriers(db) == []
    assert nearby_material_vendors(db, fabric="cotton") == []
    db.execute.assert_not_called()


@pytest.mark.parametrize("finder,kwargs", [
    (nearby_professionals, {}),
    (nearby_available_couriers, {}),
    (nearby_material_vendors, {"fabric": "cotton"}),
])
def test_spatial_queries_use_indexable_postgis_distance(finder, kwargs):
    db = Mock()
    db.execute.return_value.all.return_value = []
    finder(db, latitude=6.52, longitude=3.38, radius_m=2500, **kwargs)
    stmt = db.execute.call_args.args[0]
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ST_DWithin" in sql
    assert "ST_Distance" in sql
    assert "is_verified" in sql
    assert "LIMIT" in sql


def test_approximate_city_fallback_never_invents_distance():
    db = Mock()
    db.execute.return_value.all.return_value = []
    nearby_professionals(db, city="Lagos", state_region="Lagos")
    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "ST_DWithin" not in sql
    assert "city" in sql
    assert "state_region" in sql


def test_vendor_search_requires_specific_fabric():
    with pytest.raises(ValueError):
        nearby_material_vendors(Mock(), fabric=" ")


def test_created_location_includes_geography_and_rejects_invalid_coordinates():
    from app.services.location_service import LocationService

    db = Mock()
    location = LocationService(db).create_location(
        latitude=6.5244, longitude=3.3792, location_type="tailor_shop",
    )
    db.add.assert_called_once_with(location)
    assert "ST_GeogFromText" in str(location.geom)
    db.commit.assert_called_once()
    with pytest.raises(ValueError):
        LocationService(Mock()).create_location(
            latitude=100, longitude=3.4, location_type="tailor_shop",
        )
