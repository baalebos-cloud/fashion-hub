"""Real persisted prerequisites shared by order and payment regressions."""
import uuid
from decimal import Decimal
from app.models.address import Address
from app.models.customer import Customer
from app.models.design import Design
from app.models.location import Location
from app.models.measurement import Measurement
from app.models.measurement_profile import MeasurementProfile
from app.models.professional import Professional


def catalog_request(db, customer, tailor, price='100.00'):
    professional = db.query(Professional).filter(Professional.user_id == tailor.id).first()
    if not professional:
        professional = Professional(user_id=tailor.id, professional_type=tailor.role, is_verified=True)
        db.add(professional)
        db.flush()
    buyer = db.query(Customer).filter(Customer.user_id == customer.id).first()
    if not buyer:
        buyer = Customer(user_id=customer.id)
        db.add(buyer)
        db.flush()
    design = Design(professional_id=professional.id, title='Catalog outfit', description='Made to measure',
                    base_price=Decimal(price), required_measurement_fields=['chest'], is_published=True)
    location = Location(location_type='customer_address', formatted_address='10 Test Street',
                        city='Lagos', state_region='Lagos', country='NG')
    profile = MeasurementProfile(customer_id=buyer.id, label='My measurements')
    db.add_all([design, location, profile])
    db.flush()
    address = Address(user_id=customer.id, location_id=location.id, label='Home',
                      recipient_name='Test Customer', recipient_phone='+2348012345678')
    db.add_all([address, Measurement(measurement_profile_id=profile.id, field_name='chest', value=92.50, unit='cm')])
    db.commit()
    return dict(customer=customer, professional_user_id=tailor.id,
                order_items=[dict(reference_type='design', reference_id=design.id, quantity=1)],
                delivery_address_id=address.id, measurement_profile_id=profile.id,
                idempotency_key=uuid.uuid4().hex)
