"""Attach a material purchase to a customer's clothing order.

No checkout, payment, escrow, payout or courier action is triggered.
Only the owning tailor/designer can link their own material purchase.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry


class MaterialOrderLinkService:
    def __init__(self, db: Session):
        self.db = db

    def attach(self, *, customer_order_id, material_order_id, actor):
        # Acquire locks in a consistent order: customer first, then vendor order.
        customer = (
            self.db.query(Order).filter(Order.id == customer_order_id)
            .with_for_update().one_or_none()
        )
        if not customer or customer.order_type != "customer_order":
            raise NotFoundError("Customer clothing order not found.")
        if actor.role not in {"tailor", "designer"} or str(customer.seller_user_id) != str(actor.id):
            raise ForbiddenError("Only the owning professional may link material orders.")
        if customer.status not in {"paid", "accepted", "in_production"}:
            raise ConflictError("Customer order cannot source materials in its current state.")
        material = (
            self.db.query(Order).filter(Order.id == material_order_id)
            .with_for_update().one_or_none()
        )
        if not material or material.order_type != "vendor_order":
            raise NotFoundError("Material purchase order not found.")
        if str(material.buyer_user_id) != str(actor.id):
            raise ForbiddenError("Only the material purchaser may link this order.")
        if material.parent_customer_order_id is not None:
            if str(material.parent_customer_order_id) == str(customer.id):
                return material  # idempotent retry
            raise ConflictError("Material purchase already belongs to a different customer order.")
        if material.status not in {"cart", "checkout", "payment_pending"}:
            raise ConflictError("Link material purchases before confirmed payment.")
        material.parent_customer_order_id = customer.id
        self.db.add(OrderTimelineEntry(
            order_id=material.id, from_status=material.status,
            to_status=material.status, actor_user_id=actor.id,
            note="Material purchase linked to customer clothing order.",
        ))
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(material)
        return material
