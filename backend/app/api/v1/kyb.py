"""
/kyb

Business verification (CAC) for vendors (required) and tailors/designers
(optional trust badge). Registry results come from Prembly when enabled;
otherwise, or when the registry is unavailable, an admin reviews the
uploaded certificate. See services/verification_service.py.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.kyb import KYBStatusResponse, SubmitKYBRequest
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/kyb", tags=["KYB"])


@router.post("", response_model=KYBStatusResponse, status_code=201)
def submit_kyb(payload: SubmitKYBRequest,
               user: User = Depends(require_roles(Role.VENDOR, Role.TAILOR, Role.DESIGNER)),
               db: Session = Depends(get_db)):
    return VerificationService(db).submit_kyb(
        user=user, registration_number=payload.business_registration_number,
        company_type=payload.company_type, document_storage_keys=payload.document_storage_keys)


@router.get("/status", response_model=KYBStatusResponse)
def kyb_status(user: User = Depends(require_roles(Role.VENDOR, Role.TAILOR, Role.DESIGNER)),
               db: Session = Depends(get_db)):
    record = VerificationService(db).latest_kyb(user.id)
    if record is None:
        raise NotFoundError("No KYB submission found.")
    return record
