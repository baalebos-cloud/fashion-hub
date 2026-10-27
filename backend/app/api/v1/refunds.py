"""Customer refund requests and explicit administrator approval, never automatic payouts."""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import Role, require_roles
from app.models.refund import Refund
from app.models.order import Order
from app.models.user import User
from app.services.refund_service import RefundService

router = APIRouter(prefix="/refunds", tags=["Refunds"])


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    order_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    reason: str = Field(min_length=5, max_length=2000)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    payment_id: UUID
    order_id: UUID
    amount: Decimal
    reason: str | None
    status: str
    provider_refund_reference: str | None


@router.get("", response_model=list[RefundResponse])
def list_refunds(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    query = db.query(Refund)
    if user.role != "admin":
        query = query.join(Order, Refund.order_id == Order.id).filter(
            or_(Order.buyer_user_id == user.id, Order.seller_user_id == user.id))
    return query.order_by(Refund.created_at.desc(), Refund.id).limit(100).all()


@router.post("", response_model=RefundResponse, status_code=201)
def request_refund(payload: RefundRequest, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return RefundService(db).request_refund(
        order_id=payload.order_id, requested_by=user, amount=payload.amount, reason=payload.reason,
    )


@router.post("/{refund_id}/approve", response_model=RefundResponse)
def approve(refund_id: UUID, user: User = Depends(require_roles(Role.ADMIN)),
            db: Session = Depends(get_db)):
    return RefundService(db).approve_refund(refund_id, approved_by=user)


@router.post("/{refund_id}/reject", response_model=RefundResponse)
def reject(refund_id: UUID, user: User = Depends(require_roles(Role.ADMIN)),
           db: Session = Depends(get_db)):
    return RefundService(db).reject_refund(refund_id, rejected_by=user)
