"""Privacy-preserving spatial discovery on existing indexed PostGIS geography.

Returns only business identifiers and distance bands, not exact coordinates.
Courier dispatch requires a separate authorized assignment transaction.
"""
import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.delivery_partner import DeliveryPartner
from app.models.location import Location
from app.models.professional import Professional
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.models.user import User


def validated_search(*, latitude=None, longitude=None, radius_m=10000,
                     city=None, state_region=None):
    if not isinstance(radius_m, (int, float)) or isinstance(radius_m, bool) or not math.isfinite(radius_m) or not 100 <= radius_m <= 50000:
        raise ValueError("Radius must be between 100 and 50000 metres.")
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude or neither.")
    if latitude is not None:
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                   for v in (latitude, longitude)):
            raise ValueError("Coordinates must be finite.")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordinates are outside valid ranges.")
        return float(latitude), float(longitude), float(radius_m), None, None
    if not city or not state_region:
        return None, None, float(radius_m), None, None
    return None, None, float(radius_m), city.strip()[:128], state_region.strip()[:128]


def _geo_filters(location, lat, lon, radius, city, state):
    if lat is None:
        return [location.city.ilike(city), location.state_region.ilike(state)], None
    origin = func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})")
    return [location.geom.is_not(None), func.ST_DWithin(location.geom, origin, radius)], func.ST_Distance(location.geom, origin)


def _public_rows(db: Session, statement, *, max_results):
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 25:
        raise ValueError("Result limit must be between 1 and 25.")
    return db.execute(statement.limit(max_results)).all()


def nearby_professionals(db: Session, *, latitude=None, longitude=None, radius_m=10000,
                         city=None, state_region=None, max_results=20):
    lat, lon, radius, city, state = validated_search(
        latitude=latitude, longitude=longitude, radius_m=radius_m,
        city=city, state_region=state_region,
    )
    if lat is None and not city:
        return []
    filters, distance = _geo_filters(Location, lat, lon, radius, city, state)
    stmt = (select(Professional.id, Professional.business_name,
                   (distance if distance is not None else func.cast(None, Location.latitude.type)).label("distance_m"))
            .join(Location, Location.id == Professional.location_id)
            .join(User, User.id == Professional.user_id)
            .where(User.is_active.is_(True),
                   Professional.is_verified.is_(True),
                   Professional.accepts_new_orders.is_(True),
                   *filters))
    stmt = stmt.order_by(distance, Professional.id) if distance is not None else stmt.order_by(Professional.id)
    return [{"id": str(r[0]), "business_name": r[1],
             "distance_m": round(float(r[2]), -2) if r[2] is not None else None}
            for r in _public_rows(db, stmt, max_results=max_results)]


def nearby_material_vendors(db: Session, *, fabric: str, latitude=None, longitude=None,
                            radius_m=10000, city=None, state_region=None, max_results=20):
    if not fabric or not fabric.strip() or len(fabric) > 80:
        raise ValueError("Provide a fabric name up to 80 characters.")
    lat, lon, radius, city, state = validated_search(
        latitude=latitude, longitude=longitude, radius_m=radius_m,
        city=city, state_region=state_region,
    )
    if lat is None and not city:
        return []
    filters, distance = _geo_filters(Location, lat, lon, radius, city, state)
    term = fabric.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    stmt = (select(Vendor.id, Vendor.business_name,
                   (distance if distance is not None else func.cast(None, Location.latitude.type)).label("distance_m"))
            .join(Location, Location.id == Vendor.warehouse_location_id)
            .join(VendorProduct, VendorProduct.vendor_id == Vendor.id)
            .join(ProductVariant, ProductVariant.product_id == VendorProduct.id)
            .join(Inventory, Inventory.product_variant_id == ProductVariant.id)
            .join(User, User.id == Vendor.user_id)
            .where(User.is_active.is_(True), User.role == "vendor",
                   Inventory.quantity_available > 0,
                   Vendor.is_verified.is_(True), VendorProduct.is_active.is_(True),
                   VendorProduct.name.ilike(f"%{term}%", escape="\\"), *filters)
            .distinct())
    stmt = stmt.order_by(distance, Vendor.id) if distance is not None else stmt.order_by(Vendor.id)
    return [{"id": str(r[0]), "business_name": r[1],
             "distance_m": round(float(r[2]), -2) if r[2] is not None else None}
            for r in _public_rows(db, stmt, max_results=max_results)]


def nearby_available_couriers(db: Session, *, latitude=None, longitude=None,
                              radius_m=10000, city=None, state_region=None,
                              max_results=20):
    lat, lon, radius, city, state = validated_search(
        latitude=latitude, longitude=longitude, radius_m=radius_m,
        city=city, state_region=state_region,
    )
    if lat is None and not city:
        return []
    filters, distance = _geo_filters(Location, lat, lon, radius, city, state)
    stmt = (select(DeliveryPartner.id,
                   (distance if distance is not None else func.cast(None, Location.latitude.type)).label("distance_m"))
            .join(Location, Location.id == DeliveryPartner.current_location_id)
            .join(User, User.id == DeliveryPartner.user_id)
            .where(User.is_active.is_(True),
                   DeliveryPartner.is_verified.is_(True),
                   DeliveryPartner.is_available.is_(True), *filters))
    stmt = stmt.order_by(distance, DeliveryPartner.id) if distance is not None else stmt.order_by(DeliveryPartner.id)
    return [{"id": str(r[0]),
             "distance_m": round(float(r[1]), -2) if r[1] is not None else None}
            for r in _public_rows(db, stmt, max_results=max_results)]
