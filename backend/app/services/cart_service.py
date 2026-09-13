"""
Cart business logic for tailors/designers purchasing vendor materials.

Edge case handled here: "vendor sells out while product is in a cart".
We do NOT reserve inventory at add-to-cart time (that would let idle carts
starve other buyers). Instead:
  - At add/update time we do a soft availability check for UX feedback.
  - At checkout time (checkout_service) we re-check + atomically decrement
    stock inside the same DB transaction as order creation, using a row
    lock, so the last buyer to actually pay wins and everyone else gets a
    clear "no longer available" error rather than an oversold order.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_active_cart(self, owner_user_id) -> Cart:
        cart = (
            self.db.query(Cart)
            .filter(Cart.owner_user_id == owner_user_id, Cart.status == "active")
            .first()
        )
        if not cart:
            cart = Cart(owner_user_id=owner_user_id, status="active")
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    def add_item(self, *, owner_user_id, product_variant_id, quantity: int) -> CartItem:
        if quantity < 1:
            raise ValidationAppError("Quantity must be at least 1.")

        variant = self.db.get(ProductVariant, product_variant_id)
        if not variant:
            raise NotFoundError("Product variant not found.")

        inventory = self.db.query(Inventory).filter(Inventory.product_variant_id == variant.id).first()
        if inventory and inventory.quantity_available < quantity:
            raise ConflictError(
                f"Only {inventory.quantity_available} unit(s) of this item are currently available."
            )

        cart = self.get_or_create_active_cart(owner_user_id)
        existing_item = (
            self.db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_variant_id == variant.id)
            .first()
        )
        if existing_item:
            existing_item.quantity += quantity
            self.db.commit()
            self.db.refresh(existing_item)
            return existing_item

        product = variant.product_id  # FK only in this scaffold; join to VendorProduct for vendor_id in a full impl.
        item = CartItem(
            cart_id=cart.id,
            product_variant_id=variant.id,
            vendor_id=variant.product_id,  # placeholder: resolve real vendor_id via VendorProduct join
            quantity=quantity,
            unit_price_snapshot=variant.price,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_quantity(self, *, cart_item_id, quantity: int) -> CartItem:
        if quantity < 1:
            raise ValidationAppError("Quantity must be at least 1.")
        item = self.db.get(CartItem, cart_item_id)
        if not item:
            raise NotFoundError("Cart item not found.")
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, cart_item_id) -> None:
        item = self.db.get(CartItem, cart_item_id)
        if item:
            self.db.delete(item)
            self.db.commit()

    def get_cart_summary(self, owner_user_id) -> dict:
        cart = self.get_or_create_active_cart(owner_user_id)
        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        subtotal = sum(float(i.unit_price_snapshot) * i.quantity for i in items)
        return {"cart_id": cart.id, "items": items, "subtotal": subtotal}
