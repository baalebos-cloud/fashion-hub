"""Explicitly idempotent refund-request API. No automatic refund execution."""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.api.v1.refunds import RefundRequest, RefundResponse
from app.services.refund_service import RefundService

router = APIRouter(prefix="/payments", tags=["Payment Safety"])


@router.post("/refund", response_model=RefundResponse, status_code=201)
def request_refund_with_key(
    payload: RefundRequest,
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=16, max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    refund = RefundService(db).request_refund(
        order_id=payload.order_id, requested_by=user, amount=payload.amount,
        reason=payload.reason, idempotency_key=idempotency_key,
    )
    try:
        from redis import Redis
        from app.core.config import settings
        Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1).setex(
            f"seam:refund:{user.id}:{idempotency_key}", 86400, str(refund.id),
        )
    except Exception:
        # Database uniqueness is authoritative, never Redis alone.
        pass
    return refund
