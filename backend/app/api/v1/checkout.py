"""One vendor order and stock reservation per revision-bound checkout."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.checkout import CheckoutRequest
from app.schemas.order import OrderResponse
from app.services.checkout_service import CheckoutService

router = APIRouter(prefix='/checkout', tags=['Checkout'])


@router.post('', response_model=OrderResponse, status_code=201)
def checkout(
    payload: CheckoutRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
    user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    if idempotency_key != payload.idempotency_key:
        raise HTTPException(status_code=409, detail="Idempotency-Key header and request body must match.")
    # Database unique key and buyer/cart fingerprint remain authoritative.
    order = CheckoutService(db).checkout_cart(buyer_user_id=user.id, **payload.model_dump())
    try:
        from redis import Redis
        from app.core.config import settings
        cache = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        cache.setex(f"seam:checkout:{user.id}:{idempotency_key}", 86400, str(order.id))
    except Exception:
        # A cache outage must never change or duplicate a completed database order.
        pass
    return order
