"""
Checkout business logic for the tailor/designer -> vendor cart flow.

Key requirement from the spec: a cart may contain products from MULTIPLE
vendors, but the buyer pays ONCE and gets ONE checkout/payment record and
ONE invoice per vendor is still generated for that vendor's accounting, tied
back to the same parent payment via `parent_order_id`/grouping metadata.

This function is the one place inventory is authoritatively decremented,
inside a single DB transaction with row-level locks on each Inventory row
(acquired in a stable, sorted order to avoid deadlocks between concurrent
checkouts touching overlapping products).
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.constants import VendorOrderStatus
from app.core.exceptions import ConflictError, ValidationAppError
from app.core.timezone import utcnow
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.utils.order_number import generate_order_number


class CheckoutService:
    def __init__(self, db: Session):
        self.db = db

    def checkout_cart(self, *, cart_id, buyer_user_id, delivery_address_id) -> list[Order]:
        cart = self.db.get(Cart, cart_id)
        if not cart or cart.status != "active":
            raise ValidationAppError("Cart is not available for checkout.")

        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        if not items:
            raise ValidationAppError("Cannot check out an empty cart.")

        # Lock inventory rows in a stable order (by product_variant_id) to
        # prevent deadlocks when two checkouts race on overlapping items.
        variant_ids = sorted({str(i.product_variant_id) for i in items})
        inventories = {
            str(inv.product_variant_id): inv
            for inv in self.db.query(Inventory)
            .filter(Inventory.product_variant_id.in_(variant_ids))
            .order_by(Inventory.product_variant_id)
            .with_for_update()
            .all()
        }

        # Edge case: vendor sold out while item sat in cart. Fail the WHOLE
        # checkout with a clear, itemized error rather than partially
        # fulfilling -- the client should let the buyer adjust quantities.
        shortfalls = []
        for item in items:
            inv = inventories.get(str(item.product_variant_id))
            if inv is None or inv.quantity_available < item.quantity:
                shortfalls.append(
                    {
                        "product_variant_id": str(item.product_variant_id),
                        "requested": item.quantity,
                        "available": inv.quantity_available if inv else 0,
                    }
                )
        if shortfalls:
            raise ConflictError(f"Some items are no longer available in the requested quantity: {shortfalls}")

        # Group line items by vendor: one Order per vendor, but all created
        # atomically and linked by a shared `idempotency_key` prefix so the
        # payment layer can charge them together as a single transaction.
        items_by_vendor: dict[str, list[CartItem]] = defaultdict(list)
        for item in items:
            items_by_vendor[str(item.vendor_id)].append(item)

        checkout_group_key = generate_order_number(prefix="CHK")
        created_orders: list[Order] = []

        for vendor_id, vendor_items in items_by_vendor.items():
            subtotal = sum(float(i.unit_price_snapshot) * i.quantity for i in vendor_items)
            order = Order(
                order_number=generate_order_number(prefix="VO"),
                order_type="vendor_order",
                buyer_user_id=buyer_user_id,
                seller_user_id=vendor_id,
                status=VendorOrderStatus.CHECKOUT.value,
                subtotal=subtotal,
                total_amount=subtotal,
                delivery_address_id=delivery_address_id,
                ordered_at=utcnow(),
                idempotency_key=f"{checkout_group_key}:{vendor_id}",
            )
            self.db.add(order)
            self.db.flush()  # get order.id before creating items

            for item in vendor_items:
                self.db.add(
                    OrderItem(
                        order_id=order.id,
                        reference_type="product_variant",
                        reference_id=item.product_variant_id,
                        name_snapshot="Vendor material",  # resolve real product name via join in full impl
                        unit_price=item.unit_price_snapshot,
                        quantity=item.quantity,
                        line_total=float(item.unit_price_snapshot) * item.quantity,
                    )
                )
                # Reserve stock immediately; released back if payment fails
                # (see payment_service failure path / a reservation-expiry job).
                inv = inventories[str(item.product_variant_id)]
                inv.quantity_available -= item.quantity
                inv.quantity_reserved += item.quantity

            created_orders.append(order)

        cart.status = "checked_out"
        self.db.commit()
        for order in created_orders:
            self.db.refresh(order)

        return created_orders
