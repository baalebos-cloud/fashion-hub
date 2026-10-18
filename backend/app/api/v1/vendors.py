"""Owned vendor profiles; only administrators can grant verification."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.models.vendor import Vendor
from app.models.audit_log import AuditLog
from app.schemas.vendor import VendorCreateRequest, VendorResponse

router = APIRouter(prefix='/vendors', tags=['Vendors'])


@router.get('/me', response_model=VendorResponse | None)
def mine(user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return db.query(Vendor).filter_by(user_id=user.id).first()


@router.post('/me', response_model=VendorResponse, status_code=201)
def create(payload: VendorCreateRequest, user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    if db.query(Vendor).filter_by(user_id=user.id).first():
        raise ConflictError('A vendor profile already exists.')
    profile = Vendor(user_id=user.id, **payload.model_dump(), is_verified=False)
    db.add(profile)
    db.commit()
    return profile


@router.post('/{vendor_id}/verify', response_model=VendorResponse)
def verify(vendor_id: uuid.UUID, user: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)):
    profile = db.query(Vendor).filter_by(id=vendor_id).with_for_update().populate_existing().first()
    if not profile:
        raise NotFoundError('Vendor not found.')
    if not profile.is_verified:
        profile.is_verified = True
        db.add(AuditLog(actor_user_id=user.id, action='vendor.verified', resource_type='vendor', resource_id=profile.id))
        db.commit()
    return profile
