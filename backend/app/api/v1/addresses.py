"""Owned postal addresses; never accept an arbitrary location/user ID."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.address import Address
from app.models.location import Location
from app.models.user import User
from app.schemas.address import AddressResponse, CreateAddressRequest

router = APIRouter(prefix='/addresses', tags=['Addresses'])


def serialize(address, location):
    return AddressResponse(
        id=address.id, label=address.label or 'Home', recipient_name=address.recipient_name,
        recipient_phone=address.recipient_phone, formatted_address=location.formatted_address,
        city=location.city, state_region=location.state_region, country=location.country,
        postal_code=location.postal_code,
    )


@router.get('', response_model=list[AddressResponse])
def list_addresses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Address, Location).join(Location, Location.id == Address.location_id)
            .filter(Address.user_id == user.id).order_by(Address.created_at.desc()).limit(100).all())
    # Incomplete legacy rows cannot be used by the new checkout. Keep them
    # intact for support rather than returning malformed address DTOs.
    return [serialize(a, loc) for a, loc in rows if all([
        a.recipient_name, a.recipient_phone, loc.formatted_address, loc.city,
        loc.state_region, loc.country and len(loc.country) == 2,
    ])]


@router.post('', response_model=AddressResponse, status_code=201)
def create_address(payload: CreateAddressRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    location = Location(location_type='customer_address', **payload.model_dump(exclude={'label', 'recipient_name', 'recipient_phone'}))
    db.add(location)
    db.flush()
    address = Address(user_id=user.id, location_id=location.id, label=payload.label,
                      recipient_name=payload.recipient_name, recipient_phone=payload.recipient_phone)
    db.add(address)
    db.commit()
    db.refresh(address)
    return serialize(address, location)
