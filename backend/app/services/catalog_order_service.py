"""Catalog checkout. This service owns the transaction; amounts are Decimal.

The request fingerprint covers the customer's intent, not mutable catalog
prices. A retry returns the original snapshot even if a listing changes.
"""
import hashlib
import json
from collections import Counter
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.config import settings
from app.core.timezone import utcnow
from app.models.address import Address
from app.models.customer import Customer
from app.models.design import Design
from app.models.location import Location
from app.models.measurement import Measurement
from app.models.measurement_profile import MeasurementProfile
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.models.user import User
from app.schemas.order import CreateCustomerOrderRequest
from app.utils.order_number import generate_order_number

MAX_AMOUNT = Decimal('9999999999.99')


class CatalogOrderService:
    def __init__(self, db):
        self.db = db

    def create(self, *, customer, professional_user_id, order_items, delivery_address_id,
               measurement_profile_id, idempotency_key):
        if customer.role != 'customer' or not customer.is_active:
            raise ForbiddenError('Only an active customer may place an order.')
        try:
            request = CreateCustomerOrderRequest(
                professional_user_id=professional_user_id, items=order_items,
                delivery_address_id=delivery_address_id, measurement_profile_id=measurement_profile_id,
                idempotency_key=idempotency_key,
            )
        except ValidationError as exc:
            raise ValidationAppError('Select published designs, a delivery address, measurements and an idempotency key.') from exc
        quantities = Counter()
        for item in request.items:
            quantities[str(item.reference_id)] += item.quantity
        if any(quantity > 100 for quantity in quantities.values()):
            raise ValidationAppError('At most 100 units of each design may be ordered.')
        intent = {
            'seller': str(request.professional_user_id), 'address': str(request.delivery_address_id),
            'measurements': str(request.measurement_profile_id), 'items': sorted(quantities.items()),
            'version': 'catalog_v1',
        }
        fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
        # Serialize retries by the same buyer. Different buyers sharing a key
        # are also protected by the existing unique constraint and conflict path.
        self.db.query(User).filter(User.id == customer.id).with_for_update().one()
        existing = self._existing(request.idempotency_key)
        if existing:
            return self._replay(existing, customer.id, fingerprint)
        seller = self.db.query(User).filter(User.id == request.professional_user_id).with_for_update(read=True).first()
        professional = self.db.query(Professional).filter(Professional.user_id == request.professional_user_id).with_for_update(read=True).first()
        if not seller or not seller.is_active or seller.role not in {'tailor', 'designer'} or not professional:
            raise NotFoundError('Professional not found.')
        if not professional.accepts_new_orders:
            raise ConflictError('This professional is not currently accepting orders.')
        # Demo visibility is not verification: the rollout flag only permits
        # pending professionals to accept catalog orders while explicitly enabled.
        if not professional.is_verified and not settings.HACKATHON_SHOW_PENDING_PROFESSIONALS:
            raise ConflictError('This professional is awaiting verification and cannot accept orders yet.')
        address = self.db.query(Address).filter(Address.id == request.delivery_address_id, Address.user_id == customer.id).with_for_update(read=True).first()
        if not address:
            raise NotFoundError('Delivery address not found.')
        location = self.db.get(Location, address.location_id)
        if not location or not all([address.recipient_name, address.recipient_phone, location.formatted_address,
                                    location.city, location.state_region, location.country]):
            raise ValidationAppError('Save a complete delivery address before ordering.')
        if location.country != 'NG':
            raise ConflictError('Catalog checkout currently supports Nigerian delivery addresses only.')
        profile = (self.db.query(MeasurementProfile).join(Customer, Customer.id == MeasurementProfile.customer_id)
                   .filter(MeasurementProfile.id == request.measurement_profile_id, Customer.user_id == customer.id).first())
        if not profile:
            raise NotFoundError('Measurement profile not found.')
        fields = self.db.query(Measurement).filter(Measurement.measurement_profile_id == profile.id).order_by(Measurement.field_name).all()
        if not fields or any(not Decimal(str(f.value)).is_finite() or f.value <= 0 or f.unit not in {'cm', 'in'} for f in fields):
            raise ValidationAppError('Save valid measurements before ordering.')
        designs = (self.db.query(Design).filter(Design.id.in_(list(quantities))).order_by(Design.id)
                   .with_for_update(read=True).all())
        if len(designs) != len(quantities) or any(not d.is_published or d.professional_id != professional.id for d in designs):
            raise ConflictError('Select published designs belonging to this professional.')
        available_fields = {f.field_name for f in fields}
        required_fields = {name for d in designs for name in (d.required_measurement_fields or [])}
        if not required_fields <= available_fields:
            raise ValidationAppError('Measurement profile is missing required fields: ' + ', '.join(sorted(required_fields - available_fields)))
        if any(d.currency != 'NGN' for d in designs):
            raise ConflictError('Catalog checkout currently supports NGN designs only.')
        items = []
        subtotal = Decimal('0.00')
        for design in designs:
            price = Decimal(str(design.base_price))
            if not price.is_finite() or price <= 0 or price != price.quantize(Decimal('0.01')):
                raise ConflictError('This design has an invalid catalog price.')
            quantity = quantities[str(design.id)]
            line_total = price * quantity
            subtotal += line_total
            items.append(OrderItem(reference_type='design', reference_id=design.id,
                                   name_snapshot=design.title, description_snapshot=design.description,
                                   unit_price=price, quantity=quantity, line_total=line_total))
        if subtotal > MAX_AMOUNT:
            raise ValidationAppError('Order exceeds the supported total.')
        order = Order(
            order_number=generate_order_number(prefix='CO'), order_type='customer_order',
            buyer_user_id=customer.id, seller_user_id=seller.id, status='pending',
            subtotal=subtotal, total_amount=subtotal, currency='NGN', delivery_fee=0, tax_amount=0, discount_amount=0,
            delivery_address_id=address.id, measurement_profile_id=profile.id,
            ordered_at=utcnow(), idempotency_key=request.idempotency_key,
            pricing_source='catalog_v1', request_fingerprint=fingerprint,
            delivery_address_snapshot={
                'recipient_name': address.recipient_name, 'recipient_phone': address.recipient_phone,
                'formatted_address': location.formatted_address, 'city': location.city,
                'state_region': location.state_region, 'country': location.country, 'postal_code': location.postal_code,
            },
            measurement_snapshot={'label': profile.label, 'garment_type': profile.garment_type,
                                  'fields': [{'field_name': f.field_name, 'value': str(f.value), 'unit': f.unit} for f in fields]},
            items=items,
        )
        try:
            self.db.add(order)
            self.db.flush()
            self.db.add(OrderTimelineEntry(order_id=order.id, to_status='pending', actor_user_id=customer.id,
                                           note='Order created from published catalog prices.'))
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self._existing(request.idempotency_key)
            if existing:
                return self._replay(existing, customer.id, fingerprint)
            raise
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(order)
        return order

    def _existing(self, key):
        return self.db.query(Order).filter(Order.idempotency_key == key).first()

    @staticmethod
    def _replay(order, buyer_id, fingerprint):
        if order.buyer_user_id != buyer_id or order.request_fingerprint != fingerprint:
            raise ConflictError('Idempotency key is already in use for a different order request.')
        return order


def assert_catalog_order_payable(order):
    """Never charge a legacy customer order whose price provenance is unknown."""
    if order.order_type != 'customer_order':
        return
    if order.pricing_source != 'catalog_v1' or not order.items or not order.delivery_address_snapshot or not order.measurement_snapshot:
        raise ConflictError('This legacy order needs to be recreated from the published catalog before payment.')
    subtotal = Decimal('0.00')
    for item in order.items:
        if item.quantity < 1 or item.unit_price <= 0 or item.line_total != item.unit_price * item.quantity:
            raise ConflictError('Order line totals require review before payment.')
        subtotal += item.line_total
    if subtotal != order.subtotal or subtotal + order.delivery_fee + order.tax_amount - order.discount_amount != order.total_amount:
        raise ConflictError('Order totals require review before payment.')
