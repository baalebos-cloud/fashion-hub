import uuid
from typing import Optional
from pydantic import BaseModel


class ReferralCodeResponse(BaseModel):
    referral_code: str
    referral_link: str


class ReferralResponse(BaseModel):
    id: uuid.UUID
    referred_user_id: uuid.UUID
    status: str
    commission_amount: Optional[float] = None
    commission_currency: Optional[str] = None
    qualified_at: Optional[str] = None
    paid_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ReferralSummaryResponse(BaseModel):
    total_referred: int
    qualified_count: int
    total_earned: float
    total_paid: float
    referrals: list[ReferralResponse]
