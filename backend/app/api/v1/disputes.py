"""Disputes: buyers report a problem with a paid order; admins resolve it (services/dispute_service.py)."""
import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import Role, require_roles
from app.models.dispute import Dispute
from app.models.order import Order
from app.models.user import User
from app.services.dispute_service import OUTCOME_LABELS, REASON_LABELS, DisputeService

router = APIRouter(tags=["Disputes"])


class OpenDisputeRequest(BaseModel):
    order_id: uuid.UUID
    reason: Literal["not_delivered", "wrong_item", "wrong_size", "damaged", "poor_quality", "other"]
    description: str = Field(min_length=10, max_length=2000)


class ResolveDisputeRequest(BaseModel):
    outcome: Literal["refund", "remake", "no_action"]
    note: str = Field(min_length=5, max_length=2000)
    refund_amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)


def _view(d: Dispute, order: Order | None = None, people: dict | None = None) -> dict:
    people = people or {}
    return {
        "id": str(d.id), "order_id": str(d.order_id), "status": d.status,
        "reason": d.reason, "reason_label": REASON_LABELS.get(d.reason, d.reason), "description": d.description,
        "outcome": d.outcome, "outcome_label": OUTCOME_LABELS.get(d.outcome) if d.outcome else None,
        "resolution_note": d.resolution_note,
        "refund_amount": float(d.refund_amount) if d.refund_amount is not None else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        **({"order_number": order.order_number, "order_type": order.order_type,
            "order_total": float(order.total_amount), "currency": order.currency,
            "buyer_name": people.get(order.buyer_user_id), "seller_name": people.get(order.seller_user_id)}
           if order is not None else {}),
    }


@router.post("/disputes", status_code=201)
def open_dispute(payload: OpenDisputeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _view(DisputeService(db).open(order_id=payload.order_id, actor=user, reason=payload.reason,
                                         description=payload.description))


@router.get("/disputes/mine")
def my_disputes(order_id: uuid.UUID | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disputes on orders you bought or sold (sellers see what was reported)."""
    return [_view(d) for d in DisputeService(db).for_user(user, order_id=order_id)]


@router.get("/admin/disputes")
def admin_disputes(status: Literal["open", "resolved"] | None = None, page: int = Query(1, ge=1),
                   page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db),
                   _: User = Depends(require_roles(Role.ADMIN))):
    total, rows = DisputeService(db).admin_list(status=status, offset=(page - 1) * page_size, limit=page_size)
    orders = {o.id: o for o in db.query(Order).filter(Order.id.in_([d.order_id for d in rows])).all()} if rows else {}
    ids = {o.buyer_user_id for o in orders.values()} | {o.seller_user_id for o in orders.values()}
    people = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}
    return {"total": total, "page": page, "page_size": page_size,
            "items": [_view(d, orders.get(d.order_id), people) for d in rows]}


@router.post("/admin/disputes/{dispute_id}/resolve")
def resolve_dispute(dispute_id: uuid.UUID, payload: ResolveDisputeRequest, request: Request,
                    db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Resolving with a refund moves money, so it needs a fresh authenticator code (like payouts)."""
    if payload.outcome == "refund":
        from app.services.admin_auth_service import AdminStepUpService
        AdminStepUpService(db).require(user=admin, token=request.headers.get("X-Admin-Step-Up"))
    return _view(DisputeService(db).resolve(dispute_id, admin=admin, outcome=payload.outcome, note=payload.note,
                                            refund_amount=payload.refund_amount))
