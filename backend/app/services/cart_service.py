"""Owned material carts. The account lock serializes all cart mutations.

Adding to a cart is an availability check only; checkout allocates stock.
"""
from decimal import Decimal
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.inventory import Inventory
from app.models.user import User
from app.services.vendor_catalog_service import assert_purchasable, catalog_rows, price_of


class CartService:
    def __init__(self, db):
        self.db = db

    def lock_buyer(self, owner_user_id):
        user = self.db.query(User).filter(User.id == owner_user_id).with_for_update().populate_existing().first()
        if not user or not user.is_active or user.role not in {'tailor', 'designer'}:
            raise ForbiddenError('Material carts are available to active tailors and designers.')
        return user

    def _active(self, owner_user_id):
        cart = self.db.query(Cart).filter(Cart.owner_user_id == owner_user_id, Cart.status == 'active').first()
        if not cart:
            cart = Cart(owner_user_id=owner_user_id, status='active', revision=0)
            self.db.add(cart)
            self.db.flush()
        return cart

    def get_or_create_active_cart(self, owner_user_id):
        self.lock_buyer(owner_user_id)
        cart = self._active(owner_user_id)
        self.db.commit()
        return cart

    @staticmethod
    def _quantity(quantity):
        if type(quantity) is not int or not 1 <= quantity <= 10000:
            raise ValidationAppError('Quantity must be an integer between 1 and 10000.')

    def _available(self, variant_id, quantity):
        row = catalog_rows(self.db, [variant_id]).get(str(variant_id))
        if not row:
            raise NotFoundError('Product variant not found.')
        assert_purchasable(row)
        inventory = self.db.query(Inventory).filter(Inventory.product_variant_id == variant_id).first()
        if not inventory or inventory.quantity_available < quantity:
            raise ConflictError('The requested quantity is no longer available.')
        return row

    def add_item(self, *, owner_user_id, product_variant_id, quantity):
        self._quantity(quantity)
        self.lock_buyer(owner_user_id)
        cart = self._active(owner_user_id)
        item = self.db.query(CartItem).filter(CartItem.cart_id == cart.id, CartItem.product_variant_id == product_variant_id).first()
        total_quantity = quantity + (item.quantity if item else 0)
        self._quantity(total_quantity)
        variant, product, vendor, _ = self._available(product_variant_id, total_quantity)
        if not item:
            if self.db.query(CartItem).filter(CartItem.cart_id == cart.id).count() >= 100:
                raise ValidationAppError('At most 100 different variants may be kept in a cart.')
            item = CartItem(cart_id=cart.id, product_variant_id=variant.id, vendor_id=vendor.id)
            self.db.add(item)
        item.quantity, item.unit_price_snapshot = total_quantity, variant.price
        cart.revision += 1
        self.db.commit()
        self.db.refresh(item)
        return item

    def _owned_item(self, owner_user_id, cart_item_id):
        self.lock_buyer(owner_user_id)
        row = (self.db.query(CartItem, Cart).join(Cart, Cart.id == CartItem.cart_id)
               .filter(CartItem.id == cart_item_id, Cart.owner_user_id == owner_user_id, Cart.status == 'active').first())
        if not row:
            raise NotFoundError('Cart item not found.')
        return row

    def update_quantity(self, *, owner_user_id, cart_item_id, quantity):
        self._quantity(quantity)
        item, cart = self._owned_item(owner_user_id, cart_item_id)
        variant, *_ = self._available(item.product_variant_id, quantity)
        item.quantity, item.unit_price_snapshot = quantity, variant.price
        cart.revision += 1
        self.db.commit()
        return item

    def remove_item(self, cart_item_id, *, owner_user_id):
        item, cart = self._owned_item(owner_user_id, cart_item_id)
        self.db.delete(item)
        cart.revision += 1
        self.db.commit()

    def get_cart_summary(self, owner_user_id):
        self.lock_buyer(owner_user_id)
        cart = self._active(owner_user_id)
        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).order_by(CartItem.id).all()
        rows = catalog_rows(self.db, [item.product_variant_id for item in items])
        inventory = {str(i.product_variant_id): i for i in self.db.query(Inventory)
                     .filter(Inventory.product_variant_id.in_([item.product_variant_id for item in items])).all()}
        response = []
        subtotal = Decimal('0.00')
        for item in items:
            variant, product, vendor, user = rows[str(item.product_variant_id)]
            price = price_of(variant)
            subtotal += price * item.quantity
            available = inventory.get(str(variant.id))
            response.append(dict(id=item.id, product_variant_id=variant.id, vendor_id=vendor.id,
                                 vendor_name=vendor.business_name, product_name=product.name, sku=variant.sku,
                                 quantity=item.quantity, unit_price_snapshot=float(price), currency=product.currency,
                                 is_available=bool(available and available.quantity_available >= item.quantity
                                                   and product.is_active and vendor.is_verified and user.is_active
                                                   and user.role == 'vendor' and product.currency == 'NGN')))
        result = dict(cart_id=cart.id, revision=cart.revision, items=response, subtotal=float(subtotal), currency='NGN')
        self.db.commit()
        return result
