"""One vendor order per checkout, with revision-bound retries and stock holds."""
import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.timezone import utcnow
from app.models.address import Address
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.location import Location
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_timeline import OrderTimelineEntry
from app.models.stock_reservation import StockReservation
from app.schemas.checkout import CheckoutRequest
from app.services.cart_service import CartService
from app.services.stock_reservation_service import SOURCE
from app.services.vendor_catalog_service import MAX_AMOUNT, assert_purchasable, catalog_rows, lock_inventory, price_of
from app.utils.order_number import generate_order_number


class CheckoutService:
    def __init__(self, db):
        self.db = db

    def checkout_cart(self, *, buyer_user_id, **payload):
        from pydantic import ValidationError
        try:
            request = CheckoutRequest(**payload)
        except ValidationError as exc:
            raise ValidationAppError('Select a vendor, current cart revision, delivery address and idempotency key.') from exc
        fingerprint = hashlib.sha256(json.dumps(request.model_dump(mode='json', exclude={'idempotency_key'}), sort_keys=True).encode()).hexdigest()
        CartService(self.db).lock_buyer(buyer_user_id)
        existing = self.db.query(Order).filter(Order.idempotency_key == request.idempotency_key).first()
        if existing:
            return self._replay(existing, buyer_user_id, fingerprint)
        cart = (self.db.query(Cart).filter(Cart.id == request.cart_id, Cart.owner_user_id == buyer_user_id)
                .with_for_update().populate_existing().first())
        if not cart:
            raise NotFoundError('Cart not found.')
        if cart.status != 'active' or cart.revision != request.cart_revision:
            raise ConflictError('The cart changed. Refresh it before checking out.')
        address = self.db.query(Address).filter(Address.id == request.delivery_address_id, Address.user_id == buyer_user_id).first()
        location = self.db.get(Location, address.location_id) if address else None
        if not address or not location:
            raise NotFoundError('Delivery address not found.')
        if not all([address.recipient_name, address.recipient_phone, location.formatted_address,
                    location.city, location.state_region, location.country == 'NG']):
            raise ValidationAppError('Save a complete Nigerian delivery address before checkout.')
        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).order_by(CartItem.product_variant_id).all()
        rows = catalog_rows(self.db, [i.product_variant_id for i in items], lock=True)
        selected = [i for i in items if str(rows[str(i.product_variant_id)][2].id) == str(request.vendor_id)]
        if not selected:
            raise ValidationAppError('This vendor has no items in the cart.')
        inventories = lock_inventory(self.db, [i.product_variant_id for i in selected])
        subtotal = Decimal('0.00')
        snapshots = []
        seller_id = None
        for item in selected:
            row = rows[str(item.product_variant_id)]
            assert_purchasable(row)
            variant, product, vendor, seller = row
            inv = inventories.get(str(variant.id))
            if not inv or inv.quantity_available < item.quantity:
                raise ConflictError('Some requested items are no longer available. Refresh the cart.')
            price = price_of(variant)
            subtotal += price * item.quantity
            seller_id = seller.id
            snapshots.append(OrderItem(reference_type='product_variant', reference_id=variant.id,
                name_snapshot=(product.name + ' (' + variant.sku + ')')[:255], description_snapshot=product.description,
                unit_price=price, quantity=item.quantity, line_total=price * item.quantity))
        if subtotal <= 0 or subtotal > MAX_AMOUNT:
            raise ValidationAppError('Order exceeds the supported total.')
        order = Order(order_number=generate_order_number(prefix='VO'), order_type='vendor_order',
                      buyer_user_id=buyer_user_id, seller_user_id=seller_id, status='checkout', subtotal=subtotal,
                      total_amount=subtotal, currency='NGN', delivery_fee=0, tax_amount=0, discount_amount=0,
                      ordered_at=utcnow(), delivery_address_id=address.id, source_cart_id=cart.id,
                      pricing_source=SOURCE, request_fingerprint=fingerprint, idempotency_key=request.idempotency_key,
                      reservation_expires_at=utcnow() + timedelta(minutes=settings.VENDOR_RESERVATION_TTL_MINUTES),
                      delivery_address_snapshot=dict(recipient_name=address.recipient_name, recipient_phone=address.recipient_phone,
                          formatted_address=location.formatted_address, city=location.city, state_region=location.state_region,
                          country=location.country, postal_code=location.postal_code), items=snapshots)
        try:
            self.db.add(order)
            self.db.flush()
            for item in selected:
                inv = inventories[str(item.product_variant_id)]
                inv.quantity_available -= item.quantity
                inv.quantity_reserved += item.quantity
                self.db.add(StockReservation(order_id=order.id, product_variant_id=item.product_variant_id,
                                              quantity=item.quantity, status='active'))
                self.db.delete(item)
            self.db.add(OrderTimelineEntry(order_id=order.id, to_status='checkout', actor_user_id=buyer_user_id,
                                          note='Material order created with reserved inventory.'))
            cart.revision += 1
            if len(selected) == len(items):
                cart.status = 'checked_out'
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(Order).filter(Order.idempotency_key == request.idempotency_key).first()
            if existing:
                return self._replay(existing, buyer_user_id, fingerprint)
            raise
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(order)
        return order

    @staticmethod
    def _replay(order, buyer_id, fingerprint):
        if str(order.buyer_user_id) != str(buyer_id) or order.request_fingerprint != fingerprint or order.pricing_source != SOURCE:
            raise ConflictError('Idempotency key is already in use for a different checkout.')
        return order
