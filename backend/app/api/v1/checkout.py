"""One vendor order and stock reservation per revision-bound checkout."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.checkout import CheckoutRequest
from app.schemas.order import OrderResponse
from app.services.checkout_service import CheckoutService

router = APIRouter(prefix='/checkout', tags=['Checkout'])


@router.post('', response_model=OrderResponse, status_code=201)
def checkout(payload: CheckoutRequest, user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)), db: Session = Depends(get_db)):
    return CheckoutService(db).checkout_cart(buyer_user_id=user.id, **payload.model_dump())
