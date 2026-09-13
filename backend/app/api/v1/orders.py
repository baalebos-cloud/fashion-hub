"""
/api/v1/orders

Endpoint surface (must match exactly, per project spec):

  GET  /api/v1/orders
  GET  /api/v1/orders/{order_id}

  POST /api/v1/orders/{order_id}/accept
  POST /api/v1/orders/{order_id}/start-production
  POST /api/v1/orders/{order_id}/ready
  POST /api/v1/orders/{order_id}/ship

  GET  /api/v1/orders/{order_id}/tracking

  POST /api/v1/orders/{order_id}/received

  GET  /api/v1/orders/{order_id}/timeline

  POST /api/v1/orders/{order_id}/review

RBAC (route-level, via require_roles) and ownership/state-machine
enforcement (service-level, via OrderService) work together: a role check
passing is never sufficient on its own -- OrderService additionally checks
that a tailor/designer owns THIS order, and that only the order's own
customer may call /received.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import CustomerOrderStatus
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.schemas.order import CreateCustomerOrderRequest, OrderResponse, OrderTransitionRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def _assert_can_view_order(order, current_user: User) -> None:
    if current_user.role != "admin" and str(current_user.id) not in {str(order.buyer_user_id), str(order.seller_user_id)}:
        raise ForbiddenError("You do not have permission to view this order.")


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    payload: CreateCustomerOrderRequest,
    current_user: User = Depends(require_roles(Role.CUSTOMER)),
    db: Session = Depends(get_db),
):
    service = OrderService(db)
    order = service.create_customer_order(
        customer=current_user,
        professional_user_id=payload.professional_user_id,
        order_items=[item.model_dump() for item in payload.items],
        delivery_address_id=payload.delivery_address_id,
        measurement_profile_id=str(payload.measurement_profile_id) if payload.measurement_profile_id else None,
        idempotency_key=payload.idempotency_key,
    )
    return order


@router.get("", response_model=list[OrderResponse])
def list_orders(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GET /api/v1/orders -- orders where the current user is the buyer
    (customers) or the seller (tailors/designers/vendors)."""
    repo = OrderRepository(db)
    if current_user.role in ("tailor", "designer", "vendor"):
        return repo.list_for_seller(current_user.id, offset=pagination.offset, limit=pagination.page_size)
    return repo.list_for_buyer(current_user.id, offset=pagination.offset, limit=pagination.page_size)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """GET /api/v1/orders/{order_id}"""
    order = OrderRepository(db).get_by_id(order_id)
    if not order:
        raise NotFoundError("Order not found.")
    _assert_can_view_order(order, current_user)
    return order


@router.post("/{order_id}/accept", response_model=OrderResponse)
def accept_order(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    """POST /api/v1/orders/{order_id}/accept"""
    service = OrderService(db)
    return service.transition(order_id=order_id, target_status=CustomerOrderStatus.ACCEPTED, actor=current_user, note=payload.note)


@router.post("/{order_id}/start-production", response_model=OrderResponse)
def start_production(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    """POST /api/v1/orders/{order_id}/start-production"""
    service = OrderService(db)
    return service.transition(order_id=order_id, target_status=CustomerOrderStatus.IN_PRODUCTION, actor=current_user, note=payload.note)


@router.post("/{order_id}/ready", response_model=OrderResponse)
def mark_ready(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    """POST /api/v1/orders/{order_id}/ready"""
    service = OrderService(db)
    return service.transition(order_id=order_id, target_status=CustomerOrderStatus.READY_FOR_DELIVERY, actor=current_user, note=payload.note)


@router.post("/{order_id}/ship", response_model=OrderResponse)
def ship_order(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    """POST /api/v1/orders/{order_id}/ship"""
    service = OrderService(db)
    return service.transition(order_id=order_id, target_status=CustomerOrderStatus.SHIPPED, actor=current_user, note=payload.note)


@router.get("/{order_id}/tracking")
def get_order_tracking(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/v1/orders/{order_id}/tracking

    Delegates to tracking_service once a Delivery exists for this order;
    returns the latest DeliveryTracking snapshot plus the provider's ETA.
    Kept as a thin route here -- business logic (including the "GPS stopped
    updating" staleness check) belongs in tracking_service, not the handler.
    """
    order = OrderRepository(db).get_by_id(order_id)
    if not order:
        raise NotFoundError("Order not found.")
    _assert_can_view_order(order, current_user)

    # TODO: from app.services.tracking_service import TrackingService
    # return TrackingService(db).get_tracking_for_order(order_id)
    return {"order_id": str(order_id), "status": order.status, "tracking": None, "note": "tracking_service not yet wired"}


@router.post("/{order_id}/received", response_model=OrderResponse)
def mark_received(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    # CRITICAL: only a CUSTOMER can call this, and OrderService additionally
    # verifies they are THIS order's buyer -- a tailor/designer can never
    # mark an order received, even via direct API manipulation.
    current_user: User = Depends(require_roles(Role.CUSTOMER)),
    db: Session = Depends(get_db),
):
    """POST /api/v1/orders/{order_id}/received"""
    service = OrderService(db)
    order = service.transition(order_id=order_id, target_status=CustomerOrderStatus.RECEIVED, actor=current_user, note=payload.note)
    # System-triggered progression RECEIVED -> COMPLETED, recorded as its
    # own timeline entry for a clean audit trail.
    return service.transition(order_id=order_id, target_status=CustomerOrderStatus.COMPLETED, actor=current_user, note="Auto-completed after customer confirmation.")


@router.get("/{order_id}/timeline")
def get_order_timeline(order_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """GET /api/v1/orders/{order_id}/timeline -- append-only status history."""
    from app.models.order_timeline import OrderTimelineEntry

    order = OrderRepository(db).get_by_id(order_id)
    if not order:
        raise NotFoundError("Order not found.")
    _assert_can_view_order(order, current_user)

    entries = (
        db.query(OrderTimelineEntry)
        .filter(OrderTimelineEntry.order_id == order_id)
        .order_by(OrderTimelineEntry.created_at.asc())
        .all()
    )
    return [
        {
            "from_status": e.from_status,
            "to_status": e.to_status,
            "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
            "note": e.note,
            "created_at": e.created_at,
        }
        for e in entries
    ]


@router.post("/{order_id}/review", status_code=201)
def review_order(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    current_user: User = Depends(require_roles(Role.CUSTOMER)),
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/orders/{order_id}/review

    Business rule: only allowed once order.status is RECEIVED or COMPLETED
    (enforced in review_service, not here). `note` is reused as the review
    comment for this scaffold endpoint -- a full implementation would use a
    dedicated ReviewCreateRequest schema with a required numeric rating.
    """
    order = OrderRepository(db).get_by_id(order_id)
    if not order:
        raise NotFoundError("Order not found.")
    if str(order.buyer_user_id) != str(current_user.id):
        raise ForbiddenError("Only the customer who placed this order can review it.")
    if order.status not in (CustomerOrderStatus.RECEIVED.value, CustomerOrderStatus.COMPLETED.value):
        from app.core.exceptions import ConflictError
        raise ConflictError("You can only review an order after it has been received.")

    # TODO: from app.services.review_service import ReviewService
    # return ReviewService(db).create_review(order=order, reviewer=current_user, comment=payload.note, score=...)
    return {"order_id": str(order_id), "comment": payload.note, "note": "review_service not yet wired"}


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: uuid.UUID,
    payload: OrderTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """POST /api/v1/orders/{order_id}/cancel (additional convenience endpoint
    required by the cancellation edge case; not in the minimal spec list)."""
    service = OrderService(db)
    return service.cancel(order_id=order_id, actor=current_user, reason=payload.note)
