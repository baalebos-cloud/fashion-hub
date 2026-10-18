"""Persisted material catalog, owned address and cart prerequisites."""
from decimal import Decimal
import uuid
from app.models.address import Address
from app.models.location import Location
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.services.cart_service import CartService


def user(db, role):
    value = User(email=uuid.uuid4().hex+'@example.com', full_name='Test', role=role, hashed_password='not-used')
    db.add(value)
    db.flush()
    return value


def catalog(db, *, stock=10, price='100.01'):
    seller = user(db, 'vendor')
    vendor = Vendor(user_id=seller.id, business_name='Verified fabrics', is_verified=True)
    db.add(vendor)
    db.flush()
    product = VendorProduct(vendor_id=vendor.id, name='Navy cotton', description='Per yard', base_price=Decimal(price))
    db.add(product)
    db.flush()
    variant = ProductVariant(product_id=product.id, sku='TEST-'+uuid.uuid4().hex, price=Decimal(price))
    db.add(variant)
    db.flush()
    inventory = Inventory(product_variant_id=variant.id, quantity_available=stock, quantity_reserved=0)
    db.add(inventory)
    db.commit()
    return seller, vendor, product, variant, inventory


def address(db, buyer):
    location = Location(location_type='customer_address', formatted_address='10 Test Street', city='Lagos', state_region='Lagos', country='NG')
    db.add(location)
    db.flush()
    value = Address(user_id=buyer.id, location_id=location.id, recipient_name='Buyer', recipient_phone='+2348012345678')
    db.add(value)
    db.commit()
    return value


def request(db, buyer, vendor, variant, *, quantity=1):
    delivery = address(db, buyer)
    service = CartService(db)
    service.add_item(owner_user_id=buyer.id, product_variant_id=variant.id, quantity=quantity)
    cart = service.get_cart_summary(buyer.id)
    return dict(buyer_user_id=buyer.id, cart_id=cart['cart_id'], cart_revision=cart['revision'], vendor_id=vendor.id,
                delivery_address_id=delivery.id, idempotency_key=uuid.uuid4().hex)
