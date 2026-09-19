"""
/referrals

Available to any authenticated role, but is most relevant to
professionals and vendors referring other professionals/vendors onto the
platform (see docs/referrals.md) -- a customer can technically hold a
referral code too, since nothing here is role-restricted, but the product
surface (the "Referrals" nav item) is only exposed on the professional and
vendor dashboards in the frontend.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.referral import ReferralCodeResponse, ReferralSummaryResponse
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/code", response_model=ReferralCodeResponse)
def get_my_referral_code(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ReferralService(db)
    code = service.get_or_create_code(current_user)
    return ReferralCodeResponse(referral_code=code, referral_link=f"{settings.APP_URL}/signup?ref={code}")


@router.get("/me", response_model=ReferralSummaryResponse)
def get_my_referrals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ReferralService(db)
    return service.get_summary_for_user(current_user.id)


@router.post("/{referral_id}/mark-paid", response_model=dict)
def mark_referral_paid(referral_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin-only -- see ReferralService.mark_paid for the role check."""
    service = ReferralService(db)
    referral = service.mark_paid(referral_id, actor=current_user)
    return {"id": str(referral.id), "status": referral.status}
