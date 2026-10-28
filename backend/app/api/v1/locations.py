"""
/locations

Create/update saved locations; precise coordinates are restricted to users who need them for fulfillment.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.services.spatial_discovery import nearby_professionals, nearby_material_vendors, nearby_available_couriers

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/health-check")
def module_placeholder():
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Locations."""
    return {"module": "Locations", "status": "not yet implemented"}


def _parameters(latitude, longitude, radius_m, city, state_region, limit):
    return dict(latitude=latitude, longitude=longitude, radius_m=radius_m,
                city=city, state_region=state_region, max_results=limit)


@router.get("/nearby-professionals")
def discover_professionals(
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=10000, ge=100, le=50000),
    city: str | None = Query(default=None, max_length=128),
    state_region: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=20, ge=1, le=25),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return nearby_professionals(
            db, **_parameters(latitude, longitude, radius_m, city, state_region, limit))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/nearby-vendors")
def discover_vendors(
    fabric: str = Query(min_length=1, max_length=80),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=10000, ge=100, le=50000),
    city: str | None = Query(default=None, max_length=128),
    state_region: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=20, ge=1, le=25),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return nearby_material_vendors(
            db, fabric=fabric,
            **_parameters(latitude, longitude, radius_m, city, state_region, limit))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/nearby-couriers")
def discover_available_couriers(
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=10000, ge=100, le=50000),
    city: str | None = Query(default=None, max_length=128),
    state_region: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=20, ge=1, le=25),
    user: User = Depends(require_roles(Role.ADMIN, Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    # Discovery is not authorization to assign an order or reveal courier GPS.
    try:
        return nearby_available_couriers(
            db, **_parameters(latitude, longitude, radius_m, city, state_region, limit))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
