"""Seller-created delivery requests, listed and claimed by verified couriers."""
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.delivery import DeliveryResponse
from app.schemas.delivery_request import DeliveryRequestResponse
from app.schemas.dispatch_marketplace import DispatchJob, MakeOfferRequest, OfferResponse, SellerDispatchView
from app.services.dispatch_marketplace_service import DispatchMarketplaceService
from app.services.internal_courier_service import InternalCourierService

router = APIRouter(prefix="/delivery-requests", tags=["Delivery Requests"])


@router.post("/orders/{order_id}", response_model=DeliveryRequestResponse, status_code=201)
def request_delivery(
    order_id: uuid.UUID,
    user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).request(order_id=order_id, actor=user)


@router.get("/available", response_model=list[DispatchJob])
def available_deliveries(
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    # Priced job cards with pickup/drop-off *areas* only; no exact addresses,
    # coordinates or customer identity before a rider is assigned.
    return DispatchMarketplaceService(db).job_board(actor=user, limit=limit)


@router.post("/{request_id}/offers", response_model=OfferResponse, status_code=201)
def make_offer(
    request_id: uuid.UUID,
    payload: MakeOfferRequest,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    """InDrive-style: the rider proposes their own fare and minutes to pickup."""
    return DispatchMarketplaceService(db).make_offer(
        request_id=request_id, actor=user, amount=payload.amount,
        eta_to_pickup_minutes=payload.eta_to_pickup_minutes)


@router.delete("/{request_id}/offers/mine", status_code=204)
def withdraw_offer(
    request_id: uuid.UUID,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    DispatchMarketplaceService(db).withdraw_offer(request_id=request_id, actor=user)


@router.get("/orders/{order_id}/dispatch", response_model=SellerDispatchView)
def seller_dispatch(
    order_id: uuid.UUID,
    user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
    db: Session = Depends(get_db),
):
    """The order's seller: suggested fare and live rider offers to choose from."""
    return DispatchMarketplaceService(db).seller_dispatch(order_id=order_id, actor=user)


@router.post("/offers/{offer_id}/accept", response_model=DeliveryResponse)
def accept_offer(
    offer_id: uuid.UUID,
    user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
    db: Session = Depends(get_db),
):
    return DispatchMarketplaceService(db).accept_offer(offer_id=offer_id, actor=user)


@router.post("/{request_id}/accept", response_model=DeliveryResponse)
def accept_delivery(
    request_id: uuid.UUID,
    user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
    db: Session = Depends(get_db),
):
    return InternalCourierService(db).accept(request_id=request_id, actor=user)
