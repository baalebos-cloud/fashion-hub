"""/verification/me: the signed-in user's verification checklist and next step."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verification", tags=["Verification"])


class VerificationStep(BaseModel):
    key: Literal["identity", "business"]
    title: str
    required: bool
    status: str
    rejection_reason: str | None
    submitted_at: datetime | None
    action: Literal["kyc", "kyb"]


class VerificationSummary(BaseModel):
    role: str
    verified: bool
    steps: list[VerificationStep]
    next_step: str | None


@router.get("/me", response_model=VerificationSummary)
def my_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return VerificationService(db).summary(user)
