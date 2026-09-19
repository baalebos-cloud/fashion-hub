"""
/kyc

Individual identity verification. NIN is compulsory for every
professional, vendor business-owner, and delivery partner -- see
kyc_service.py::submit and docs/nin-verification.md.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.kyc import KYCStatusResponse, SubmitKYCRequest
from app.services.kyc_service import KYCService

router = APIRouter(prefix="/kyc", tags=["KYC"])


@router.post("", response_model=KYCStatusResponse, status_code=201)
def submit_kyc(payload: SubmitKYCRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = KYCService(db)
    return service.submit(
        user_id=current_user.id,
        nin_number=payload.nin_number,
        document_storage_keys=payload.document_storage_keys,
        home_latitude=payload.home_latitude,
        home_longitude=payload.home_longitude,
        home_formatted_address=payload.home_formatted_address,
    )


@router.get("/status", response_model=KYCStatusResponse)
def get_kyc_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.repositories.kyc_repository import KYCRepository

    verification = KYCRepository(db).get_latest_kyc_for_user(current_user.id)
    if not verification:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("No KYC submission found.")
    return verification
