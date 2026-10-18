"""Owned professional carts; availability here is advisory until checkout."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.cart import AddCartItemRequest, UpdateCartItemRequest, CartSummaryResponse
from app.services.cart_service import CartService

router = APIRouter(prefix='/carts', tags=['Carts'])
buyer = require_roles(Role.TAILOR, Role.DESIGNER)


@router.get('/summary', response_model=CartSummaryResponse)
def summary(user: User = Depends(buyer), db: Session = Depends(get_db)):
    return CartService(db).get_cart_summary(user.id)


@router.post('/items', response_model=CartSummaryResponse, status_code=201)
def add(payload: AddCartItemRequest, user: User = Depends(buyer), db: Session = Depends(get_db)):
    service = CartService(db)
    service.add_item(owner_user_id=user.id, **payload.model_dump())
    return service.get_cart_summary(user.id)


@router.patch('/items/{item_id}', response_model=CartSummaryResponse)
def update(item_id: uuid.UUID, payload: UpdateCartItemRequest, user: User = Depends(buyer), db: Session = Depends(get_db)):
    service = CartService(db)
    service.update_quantity(cart_item_id=item_id, owner_user_id=user.id, quantity=payload.quantity)
    return service.get_cart_summary(user.id)


@router.delete('/items/{item_id}', status_code=204)
def remove(item_id: uuid.UUID, user: User = Depends(buyer), db: Session = Depends(get_db)):
    CartService(db).remove_item(item_id, owner_user_id=user.id)
