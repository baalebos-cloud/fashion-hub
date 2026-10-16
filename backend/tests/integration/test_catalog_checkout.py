"""Catalog price provenance, atomic snapshots, HTTP checkout and retry safety."""
from decimal import Decimal
from unittest.mock import MagicMock, patch
import uuid

from fastapi.testclient import TestClient
import pytest
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.integrations.payments.base import InitializePaymentResult, VerifyPaymentResult
from app.main import app
from app.models.address import Address
from app.models.design import Design
from app.models.location import Location
from app.models.measurement import Measurement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_timeline import OrderTimelineEntry
from app.models.payment import Payment
from app.models.professional import Professional
from app.models.user import User
from app.services.order_service import OrderService
from app.services.payment_outbox_service import PaymentOutboxService
from app.services.payment_service import PaymentService
from tests.catalog_helpers import catalog_request


@pytest.fixture()
def context(db, make_user):
    customer = make_user()
    tailor = make_user(role='tailor')
    return catalog_request(db, customer, tailor, price='100.01')


def test_catalog_prices_items_and_private_snapshots_are_atomic(db, context):
    context['order_items'] *= 3
    order = OrderService(db).create_customer_order(**context)
    assert order.total_amount == Decimal('300.03')
    assert len(order.items) == 1 and order.items[0].quantity == 3
    assert order.items[0].unit_price == Decimal('100.01')
    assert order.items[0].name_snapshot == 'Catalog outfit'
    assert order.delivery_address_snapshot['city'] == 'Lagos'
    assert order.measurement_snapshot['fields'][0]['value'] == '92.50'
    assert db.query(OrderTimelineEntry).filter_by(order_id=order.id).count() == 1
    design = db.get(Design, context['order_items'][0]['reference_id'])
    design.title, design.base_price, design.is_published = 'Changed', Decimal('900'), False
    address = db.get(Address, context['delivery_address_id'])
    db.get(Location, address.location_id).city = 'Abuja'
    db.commit()
    replay = OrderService(db).create_customer_order(**context)
    assert replay.id == order.id
    assert replay.total_amount == Decimal('300.03')
    assert replay.items[0].name_snapshot == 'Catalog outfit'
    assert replay.delivery_address_snapshot['city'] == 'Lagos'


def test_reusing_key_for_a_different_request_conflicts(db, context):
    OrderService(db).create_customer_order(**context)
    context['order_items'][0]['quantity'] = 2
    with pytest.raises(ConflictError):
        OrderService(db).create_customer_order(**context)


@pytest.mark.parametrize('change', ['price', 'empty', 'quantity', 'service', 'missing_address', 'missing_profile',
                                  'unpublished', 'wrong_professional', 'currency', 'required_fields', 'unverified'])
def test_invalid_checkout_never_creates_partial_records(db, context, change):
    design = db.get(Design, context['order_items'][0]['reference_id'])
    if change == 'price': context['order_items'][0]['unit_price'] = 0.01
    if change == 'empty': context['order_items'] = []
    if change == 'quantity': context['order_items'][0]['quantity'] = 101
    if change == 'service': context['order_items'][0]['reference_type'] = 'service'
    if change == 'missing_address': context['delivery_address_id'] = uuid.uuid4()
    if change == 'missing_profile': context['measurement_profile_id'] = uuid.uuid4()
    if change == 'unpublished': design.is_published = False
    if change == 'wrong_professional': design.professional_id = uuid.uuid4()
    if change == 'currency': design.currency = 'USD'
    if change == 'required_fields': design.required_measurement_fields = ['waist', 'sleeve_length']
    if change == 'unverified': db.get(Professional, design.professional_id).is_verified = False
    db.commit()
    with pytest.raises((ValidationAppError, ConflictError, NotFoundError)):
        OrderService(db).create_customer_order(**context)
    assert db.query(Order).count() == 0
    assert db.query(OrderItem).count() == 0
    assert db.query(OrderTimelineEntry).count() == 0


def test_foreign_address_and_measurements_are_rejected(db, context, make_user):
    other = make_user()
    other_request = catalog_request(db, other, db.get(User, context['professional_user_id']))
    for name in ['delivery_address_id', 'measurement_profile_id']:
        request = {**context, name: other_request[name]}
        with pytest.raises(NotFoundError):
            OrderService(db).create_customer_order(**request)
    assert db.query(Order).count() == 0


def test_failed_order_commit_rolls_back_items_and_timeline(db, context):
    with patch.object(db, 'commit', side_effect=RuntimeError('lost commit')), pytest.raises(RuntimeError):
        OrderService(db).create_customer_order(**context)
    db.rollback()
    assert db.query(Order).count() == db.query(OrderItem).count() == db.query(OrderTimelineEntry).count() == 0


def test_payment_initialization_is_resumable_and_uses_saved_amount(db, context):
    order = OrderService(db).create_customer_order(**context)
    provider = MagicMock()
    provider.initialize_payment.return_value = InitializePaymentResult('test-session', 'https://checkout.paystack.com/test', {})
    with patch('app.services.payment_service.get_payment_provider', return_value=provider):
        service = PaymentService(db)
        args = dict(order_id=order.id, buyer_user_id=order.buyer_user_id, customer_email=context['customer'].email,
                    callback_url='http://localhost:5173/payment/success')
        first = service.initialize_payment_for_order(**args)
        assert service.initialize_payment_for_order(**args) == first
        provider.initialize_payment.assert_called_once()
        assert provider.initialize_payment.call_args.kwargs['amount'] == 100.01
        assert db.query(Payment).count() == 1
        with pytest.raises(ValidationAppError):
            service.initialize_payment_for_order(**{**args, 'callback_url': 'https://attacker.test/callback'})


def test_legacy_pending_orders_and_corrupt_totals_cannot_start_payments(db, context):
    order = OrderService(db).create_customer_order(**context)
    with patch('app.services.payment_service.get_payment_provider') as provider:
        service = PaymentService(db)
        args = dict(order_id=order.id, buyer_user_id=order.buyer_user_id, customer_email=context['customer'].email,
                    callback_url='http://localhost:5173/payment/success')
        order.pricing_source = None
        db.commit()
        with pytest.raises(ConflictError): service.initialize_payment_for_order(**args)
        order.pricing_source, order.total_amount = 'catalog_v1', Decimal('0.01')
        db.commit()
        with pytest.raises(ConflictError): service.initialize_payment_for_order(**args)
        provider.return_value.initialize_payment.assert_not_called()


def test_http_catalog_order_payment_and_invoice_with_ownership(db, context, make_user):
    customer = context['customer']
    current = [customer]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    provider = MagicMock()
    provider.initialize_payment.return_value = InitializePaymentResult('http-checkout', 'https://checkout.paystack.com/http-test', {})
    try:
        with TestClient(app) as client, patch('app.services.payment_service.get_payment_provider', return_value=provider):
            address = client.post('/api/v1/addresses', json=dict(label='Office', recipient_name='Customer', recipient_phone='+2348012345678',
                                  formatted_address='25 Test Avenue', city='Lagos', state_region='Lagos', country='NG'))
            assert address.status_code == 201, address.text
            measurements = client.post('/api/v1/measurements', json=dict(label='New profile', fields=[dict(field_name='chest', value=93.25, unit='cm')]))
            assert measurements.status_code == 201, measurements.text
            body = dict(professional_user_id=str(context['professional_user_id']), items=[dict(reference_type='design', reference_id=str(context['order_items'][0]['reference_id']), quantity=2)],
                        delivery_address_id=address.json()['id'], measurement_profile_id=measurements.json()['id'], idempotency_key=uuid.uuid4().hex)
            tampered = {**body, 'items': [{**body['items'][0], 'unit_price': 0.01}]}
            assert client.post('/api/v1/orders', json=tampered).status_code == 422
            response = client.post('/api/v1/orders', json=body)
            assert response.status_code == 201, response.text
            order = response.json()
            assert order['total_amount'] == 200.02 and len(order['items']) == 1
            assert 'measurement_snapshot' not in order
            assert client.post('/api/v1/orders', json=body).json()['id'] == order['id']
            initialized = client.post('/api/v1/payments', json=dict(order_id=order['id'], callback_url='http://localhost:5173/customer/payment/success'))
            assert initialized.status_code in {200, 201}, initialized.text
            provider.verify_payment.return_value = VerifyPaymentResult('http-checkout', 'successful', 200.02, 'NGN', None, {})
            verified = client.get('/api/v1/payments/http-checkout/verify')
            assert verified.status_code == 200, verified.text
            assert verified.json()['status'] == 'successful'
            assert verified.json()['paid_at']
            payment_id = uuid.UUID(verified.json()['id'])
            assert PaymentOutboxService(db).process_one(payment_id=payment_id)
            invoice = client.get('/api/v1/invoices/by-order/' + order['id'])
            assert invoice.status_code == 200, invoice.text
            assert invoice.json()['line_items_snapshot'][0]['quantity'] == 2
            assert invoice.json()['total_amount'] == 200.02
            current[0] = make_user()
            assert client.get('/api/v1/addresses').json() == []
            assert client.get('/api/v1/measurements').json() == []
            assert client.get('/api/v1/orders/' + order['id']).status_code == 403
            assert client.get('/api/v1/invoices/' + invoice.json()['id']).status_code == 403
            assert client.get('/api/v1/invoices/by-order/' + order['id']).status_code == 403
    finally:
        app.dependency_overrides.clear()
