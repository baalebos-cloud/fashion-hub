"""Postgres allocation, atomic payment and independent transaction races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import MagicMock, patch
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.timezone import utcnow
from app.integrations.payments.base import InitializePaymentResult, VerifyPaymentResult
from app.main import app
from app.models.cart_item import CartItem
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.payment import Payment
from app.models.payment_outbox import PaymentOutbox
from app.models.payout import Payout
from app.models.stock_reservation import StockReservation
from app.services.cart_service import CartService
from app.services.checkout_service import CheckoutService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.payout_service import PayoutService
from app.services.stock_reservation_service import StockReservationService
from tests.vendor_helpers import catalog, user, request, address
from tests.integration.test_migrations import migration_database, migrate


@pytest.fixture()
def context(db, make_user):
    buyer = make_user(role='tailor')
    _, vendor, product, variant, inventory = catalog(db)
    return request(db, buyer, vendor, variant, quantity=2), buyer, product, inventory


def counters(db, inventory):
    db.refresh(inventory)
    return inventory.quantity_available, inventory.quantity_reserved


def payment(db, order, provider, status='successful'):
    value = Payment(order_id=order.id, provider='paystack', provider_reference=uuid.uuid4().hex,
                    amount=order.total_amount, currency='NGN', status='initialized')
    db.add(value)
    db.commit()
    provider.verify_payment.return_value = VerifyPaymentResult(value.provider_reference, status, value.amount, 'NGN', None, {})
    return value


def test_checkout_snapshots_real_vendor_and_current_decimal_price_and_retains_other_vendor(db, context):
    args, buyer, product, inventory = context
    _, _, _, second, _ = catalog(db)
    CartService(db).add_item(owner_user_id=buyer.id, product_variant_id=second.id, quantity=1)
    args['cart_revision'] = CartService(db).get_cart_summary(buyer.id)['revision']
    # Cart prices are advisory. The committed order uses the catalog again.
    from app.models.product_variant import ProductVariant
    db.get(ProductVariant, inventory.product_variant_id).price = Decimal('101.03')
    db.commit()
    order = CheckoutService(db).checkout_cart(**args)
    assert order.total_amount == Decimal('202.06')
    assert order.seller_user_id != args['vendor_id']
    assert order.items[0].name_snapshot.startswith('Navy cotton')
    assert order.delivery_address_snapshot['city'] == 'Lagos'
    assert counters(db, inventory) == (8, 2)
    assert db.query(CartItem).filter_by(cart_id=args['cart_id']).one().product_variant_id == second.id
    product.name = 'Changed'
    db.commit()
    assert CheckoutService(db).checkout_cart(**args).id == order.id
    assert counters(db, inventory) == (8, 2)
    assert order.items[0].name_snapshot.startswith('Navy cotton')
    with pytest.raises(ConflictError):
        CheckoutService(db).checkout_cart(**{**args, 'cart_revision': args['cart_revision'] + 1})


@pytest.mark.parametrize('change', ['stale', 'foreign_cart', 'foreign_address', 'stock', 'unverified', 'inactive', 'currency', 'price', 'client_price'])
def test_rejected_checkout_has_no_partial_stock_or_order(db, context, change):
    args, buyer, product, inventory = context
    if change == 'stale': args['cart_revision'] += 1
    if change == 'foreign_cart': args['buyer_user_id'] = user(db, 'designer').id
    if change == 'foreign_address': args['delivery_address_id'] = address(db, user(db, 'tailor')).id
    if change == 'stock': inventory.quantity_available = 1
    if change == 'unverified':
        from app.models.vendor import Vendor
        db.get(Vendor, args['vendor_id']).is_verified = False
    if change == 'inactive': product.is_active = False
    if change == 'currency': product.currency = 'USD'
    if change == 'price':
        from app.models.product_variant import ProductVariant
        db.get(ProductVariant, inventory.product_variant_id).price = 0
    if change == 'client_price': args['total_amount'] = 0.01
    db.commit()
    with pytest.raises((ConflictError, NotFoundError, ValidationAppError)):
        CheckoutService(db).checkout_cart(**args)
    db.rollback()
    assert db.query(StockReservation).count() == db.query(Order).filter_by(pricing_source='vendor_catalog_v1').count() == 0
    assert counters(db, inventory)[1] == 0


@pytest.mark.parametrize('lost_ack', [False, True])
def test_checkout_commit_failure_or_lost_ack_is_retry_safe(db, context, lost_ack):
    args, _, _, inventory = context
    commit = db.commit
    def failure():
        if lost_ack: commit()
        raise RuntimeError('injected')
    with patch.object(db, 'commit', side_effect=failure), pytest.raises(RuntimeError):
        CheckoutService(db).checkout_cart(**args)
    assert counters(db, inventory) == ((8, 2) if lost_ack else (10, 0))
    order = CheckoutService(db).checkout_cart(**args)
    assert counters(db, inventory) == (8, 2)
    assert db.query(StockReservation).filter_by(order_id=order.id).count() == 1


@pytest.mark.parametrize('action', ['cancel', 'expiry', 'failed'])
def test_release_is_durable_once_and_late_payment_goes_to_review(db, context, action):
    args, buyer, _, inventory = context
    order = CheckoutService(db).checkout_cart(**args)
    provider = MagicMock()
    value = payment(db, order, provider, 'failed' if action == 'failed' else 'successful')
    with patch('app.services.payment_service.get_payment_provider', return_value=provider):
        if action == 'cancel':
            OrderService(db).cancel(order_id=order.id, actor=buyer)
            OrderService(db).cancel(order_id=order.id, actor=buyer)
        elif action == 'expiry':
            order.reservation_expires_at = utcnow() - timedelta(seconds=1)
            db.commit()
            assert StockReservationService(db).expire_one()
            assert not StockReservationService(db).expire_one()
        else:
            PaymentService(db).verify_and_confirm(value.provider_reference)
        assert counters(db, inventory) == (10, 0)
        provider.verify_payment.return_value = VerifyPaymentResult(value.provider_reference, 'successful', value.amount, 'NGN', None, {})
        PaymentService(db).verify_and_confirm(value.provider_reference)
        PaymentService(db).verify_and_confirm(value.provider_reference)
    assert order.status == 'cancelled'
    assert value.status == 'successful'
    assert counters(db, inventory) == (10, 0)
    assert db.query(Payout).filter_by(order_id=order.id).count() == 0
    assert db.query(PaymentOutbox).filter_by(payment_id=value.id).one().kind == 'payment.review'


def test_settlement_and_stock_roll_back_together_then_retry_consumes_once(db, context):
    args, buyer, _, inventory = context
    order = CheckoutService(db).checkout_cart(**args)
    provider = MagicMock()
    value = payment(db, order, provider)
    with patch('app.services.payment_service.get_payment_provider', return_value=provider):
        with patch.object(PayoutService, 'create_for_order', side_effect=RuntimeError('injected')), pytest.raises(RuntimeError):
            PaymentService(db).verify_and_confirm(value.provider_reference)
        assert counters(db, inventory) == (8, 2)
        assert db.get(StockReservation, db.query(StockReservation.id).scalar()).status == 'active'
        assert db.get(Order, order.id).status == 'checkout'
        PaymentService(db).verify_and_confirm(value.provider_reference)
        PaymentService(db).verify_and_confirm(value.provider_reference)
    assert counters(db, inventory) == (8, 0)
    assert db.query(StockReservation).one().status == 'consumed'
    assert db.query(Payout).filter_by(order_id=order.id).count() == 1
    with pytest.raises(ConflictError): OrderService(db).cancel(order_id=order.id, actor=buyer)


def test_expired_hold_cannot_initialize_payment_even_without_expiry_worker(db, context):
    args, _, _, inventory = context
    order = CheckoutService(db).checkout_cart(**args)
    order.reservation_expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    with patch('app.services.payment_service.get_payment_provider') as provider:
        with pytest.raises(ConflictError):
            PaymentService(db).initialize_payment_for_order(order_id=order.id, buyer_user_id=order.buyer_user_id,
                customer_email='buyer@example.com', callback_url='http://localhost:5173/payment/success')
        provider.return_value.initialize_payment.assert_not_called()
    assert counters(db, inventory) == (10, 0)
    assert order.status == 'cancelled'


@pytest.mark.parametrize('same_buyer', [False, True])
def test_two_transactions_last_unit_or_duplicate_retry(migration_database, same_buyer):
    engine, config = migration_database
    migrate(engine, config, 'head')
    with Session(engine) as db:
        _, vendor, _, variant, inv = catalog(db, stock=1)
        first = user(db, 'tailor')
        a = request(db, first, vendor, variant)
        b = a.copy() if same_buyer else request(db, user(db, 'designer'), vendor, variant)
        variant_id = variant.id
    barrier = Barrier(2)
    def checkout(args):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try: return CheckoutService(db).checkout_cart(**args).id
            except ConflictError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(checkout, args) for args in (a, b)]
        results = [f.result(timeout=20) for f in futures]
    if same_buyer: assert results[0] == results[1] and results[0]
    else: assert sum(r is not None for r in results) == 1
    with Session(engine) as db:
        inv = db.query(Inventory).filter_by(product_variant_id=variant_id).one()
        assert (inv.quantity_available, inv.quantity_reserved) == (0, 1)
        assert db.query(StockReservation).count() == db.query(Order).count() == 1


def test_http_catalog_cart_checkout_payment_and_invoice(db, make_user):
    from app.services.payment_outbox_service import PaymentOutboxService
    from app.models.user import User
    current = [make_user(role='vendor')]
    vendor_user = current[0]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    provider = MagicMock()
    provider.initialize_payment.return_value = InitializePaymentResult('stock-http', 'https://checkout.paystack.com/stock', {})
    try:
        with TestClient(app) as client, patch('app.services.payment_service.get_payment_provider', return_value=provider):
            profile = client.post('/api/v1/vendors/me', json={'business_name': 'HTTP fabric store'})
            assert profile.status_code == 201, profile.text
            vendor_id = profile.json()['id']
            product = client.post('/api/v1/vendor-products', json={'name': 'Cotton', 'base_price': 25.03, 'initial_stock': 3})
            assert product.status_code == 201, product.text
            assert client.get('/api/v1/vendor-products').json()['total'] == 0
            assert client.post(f'/api/v1/vendors/{vendor_id}/verify').status_code == 403
            current[0] = make_user(role='admin')
            assert client.post(f'/api/v1/vendors/{vendor_id}/verify').status_code == 200
            current[0] = make_user(role='designer')
            buyer = current[0]
            assert client.get('/api/v1/vendor-products').json()['total'] == 1
            variant_id = product.json()['variants'][0]['id']
            cart = client.post('/api/v1/carts/items', json={'product_variant_id': variant_id, 'quantity': 2})
            assert cart.status_code == 201, cart.text
            summary = cart.json()
            assert summary['items'][0]['vendor_id'] == vendor_id
            delivery = address(db, buyer)
            body = dict(cart_id=summary['cart_id'], cart_revision=summary['revision'], vendor_id=vendor_id,
                        delivery_address_id=str(delivery.id), idempotency_key=uuid.uuid4().hex)
            assert client.post('/api/v1/checkout', json={**body, 'total_amount': 1}, headers={'Idempotency-Key': body['idempotency_key']}).status_code == 422
            created = client.post('/api/v1/checkout', json=body, headers={'Idempotency-Key': body['idempotency_key']})
            assert created.status_code == 201, created.text
            order = created.json()
            assert order['total_amount'] == 50.06 and order['seller_user_id'] == str(vendor_user.id)
            assert 'delivery_address_snapshot' not in order
            assert client.get('/api/v1/orders?perspective=buying&order_type=vendor_order').json()[0]['id'] == order['id']
            assert client.get('/api/v1/orders?perspective=selling').json() == []
            initialized = client.post('/api/v1/payments', json={'order_id': order['id'], 'callback_url': 'http://localhost:5173/payment/success'})
            assert initialized.status_code == 200, initialized.text
            provider.verify_payment.return_value = VerifyPaymentResult('stock-http', 'successful', 50.06, 'NGN', None, {})
            verified = client.get('/api/v1/payments/stock-http/verify')
            assert verified.status_code == 200, verified.text
            assert verified.json()['requires_review'] is False
            assert PaymentOutboxService(db).process_one(payment_id=uuid.UUID(verified.json()['id']))
            invoice = client.get('/api/v1/invoices/by-order/' + order['id'])
            assert invoice.status_code == 200, invoice.text
            assert invoice.json()['line_items_snapshot'][0]['quantity'] == 2
            current[0] = make_user(role='tailor')
            assert client.get('/api/v1/payments/stock-http/verify').status_code == 403
            assert client.get('/api/v1/orders/' + order['id']).status_code == 403
            assert client.post('/api/v1/vendor-inventory/' + variant_id + '/restock', json={'quantity_to_add': 5}).status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('competing', ['cancel', 'expiry', 'failure'])
def test_settlement_racing_release_keeps_finance_and_stock_consistent(migration_database, competing):
    engine, config = migration_database
    migrate(engine, config, 'head')
    with Session(engine) as db:
        _, vendor, _, variant, inv = catalog(db, stock=1)
        buyer = user(db, 'tailor')
        args = request(db, buyer, vendor, variant)
        order = CheckoutService(db).checkout_cart(**args)
        provider = MagicMock()
        pay = payment(db, order, provider)
        order_id, buyer_id, inv_id, reference = order.id, buyer.id, inv.id, pay.provider_reference
        if competing == 'expiry':
            order.reservation_expires_at = utcnow() - timedelta(seconds=1)
            db.commit()
    barrier = Barrier(2)
    def settle(status):
        with Session(engine) as db:
            service = PaymentService(db)
            value = db.query(Payment).filter_by(provider_reference=reference).one()
            result = VerifyPaymentResult(reference, status, value.amount, 'NGN', None, {})
            barrier.wait(timeout=10)
            service._settle(reference, result, 'race-'+status, 'payment.verified')
    def release():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            if competing == 'expiry': StockReservationService(db).expire_one()
            else:
                from app.models.user import User
                try: OrderService(db).cancel(order_id=order_id, actor=db.get(User, buyer_id))
                except ConflictError: pass  # settlement won; paid stock is never returned
    with patch('app.services.payment_service.get_payment_provider', return_value=provider), ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(settle, 'successful'), pool.submit(settle, 'failed') if competing == 'failure' else pool.submit(release)]
        for future in futures: future.result(timeout=20)
    with Session(engine) as db:
        order, inv = db.get(Order, order_id), db.get(Inventory, inv_id)
        work = db.query(PaymentOutbox).one()
        assert db.query(Payment).one().status == 'successful'
        assert inv.quantity_reserved == 0
        if order.status == 'paid':
            assert inv.quantity_available == 0 and work.kind == 'payment.settled'
            assert db.query(Payout).count() == 1
            assert db.query(StockReservation).one().status == 'consumed'
        else:
            assert order.status == 'cancelled' and inv.quantity_available == 1 and work.kind == 'payment.review'
            assert db.query(Payout).count() == 0
            assert db.query(StockReservation).one().status == 'released'


def test_cart_mutation_and_checkout_serialize_the_revision(migration_database):
    engine, config = migration_database
    migrate(engine, config, 'head')
    with Session(engine) as db:
        _, vendor, _, variant, inv = catalog(db, stock=3)
        buyer = user(db, 'tailor')
        args = request(db, buyer, vendor, variant)
        item_id = db.query(CartItem).one().id
        inv_id = inv.id
    barrier = Barrier(2)
    def checkout():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try: return CheckoutService(db).checkout_cart(**args).id
            except ConflictError: return None
    def mutate():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try: CartService(db).update_quantity(owner_user_id=args['buyer_user_id'], cart_item_id=item_id, quantity=2)
            except NotFoundError: pass  # checkout consumed the original line
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(checkout), pool.submit(mutate)
        order_id = a.result(timeout=20)
        b.result(timeout=20)
    with Session(engine) as db:
        inv = db.get(Inventory, inv_id)
        if order_id:
            assert (inv.quantity_available, inv.quantity_reserved) == (2, 1)
            assert db.query(Order).one().items[0].quantity == 1
        else:
            assert (inv.quantity_available, inv.quantity_reserved) == (3, 0)
            assert db.query(CartItem).one().quantity == 2


def test_restock_is_owned_additive_and_preserves_holds(db, context, make_user):
    from app.services.inventory_service import InventoryService
    from app.models.vendor import Vendor
    args, _, _, inv = context
    order = CheckoutService(db).checkout_cart(**args)
    service = InventoryService(db)
    with pytest.raises(NotFoundError):
        service.restock(inv.product_variant_id, owner_user_id=make_user(role='vendor').id, quantity_to_add=3, idempotency_key=uuid.uuid4().hex)
    owner = db.get(Vendor, args['vendor_id']).user_id
    result = service.restock(inv.product_variant_id, owner_user_id=owner, quantity_to_add=3, idempotency_key=uuid.uuid4().hex)
    assert (result['quantity_available'], result['quantity_reserved']) == (11, 2)
    assert result['product_name'] == 'Navy cotton'
    with pytest.raises(ConflictError):
        service.restock(inv.product_variant_id, owner_user_id=owner, quantity_to_add=1000000000, idempotency_key=uuid.uuid4().hex)


def test_stock_deadline_is_rechecked_after_waiting_for_inventory(db, context):
    from app.services import stock_reservation_service as module
    args, _, _, inv = context
    order = CheckoutService(db).checkout_cart(**args)
    provider = MagicMock()
    value = payment(db, order, provider)
    before = utcnow()
    clock = [before]
    original = module.lock_inventory
    def lock_after_delay(session, ids):
        rows = original(session, ids)
        clock[0] = order.reservation_expires_at + timedelta(seconds=1)
        return rows
    with patch('app.services.payment_service.get_payment_provider', return_value=provider), patch.object(module, 'utcnow', side_effect=lambda: clock[0]), patch.object(module, 'lock_inventory', side_effect=lock_after_delay):
        PaymentService(db).verify_and_confirm(value.provider_reference)
    assert db.get(Order, order.id).status == 'cancelled'
    assert counters(db, inv) == (10, 0)
    assert db.query(PaymentOutbox).filter_by(payment_id=value.id).one().kind == 'payment.review'


def test_restock_and_checkout_cannot_lose_counter_updates(migration_database):
    from app.services.inventory_service import InventoryService
    engine, config = migration_database
    migrate(engine, config, 'head')
    with Session(engine) as db:
        seller, vendor, _, variant, inv = catalog(db, stock=1)
        args = request(db, user(db, 'tailor'), vendor, variant)
        seller_id, variant_id = seller.id, variant.id
    barrier = Barrier(2)
    def checkout():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            CheckoutService(db).checkout_cart(**args)
    def restock():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            InventoryService(db).restock(variant_id, owner_user_id=seller_id, quantity_to_add=5, idempotency_key=uuid.uuid4().hex)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(checkout), pool.submit(restock)]
        for future in futures: future.result(timeout=20)
    with Session(engine) as db:
        inv = db.query(Inventory).filter_by(product_variant_id=variant_id).one()
        assert (inv.quantity_available, inv.quantity_reserved) == (5, 1)


@pytest.mark.parametrize('lost_ack', [False, True])
def test_restock_commit_and_retry_cannot_add_units_twice(db, context, lost_ack):
    from app.services.inventory_service import InventoryService
    from app.models.inventory_restock import InventoryRestock
    from app.models.vendor import Vendor
    args, _, _, inv = context
    owner = db.get(Vendor, args['vendor_id']).user_id
    key = uuid.uuid4().hex
    service = InventoryService(db)
    commit = db.commit
    def failure():
        if lost_ack: commit()
        raise RuntimeError('lost restock acknowledgement')
    with patch.object(db, 'commit', side_effect=failure), pytest.raises(RuntimeError):
        service.restock(inv.product_variant_id, owner_user_id=owner, quantity_to_add=3, idempotency_key=key)
    assert counters(db, inv) == ((13, 0) if lost_ack else (10, 0))
    service.restock(inv.product_variant_id, owner_user_id=owner, quantity_to_add=3, idempotency_key=key)
    service.restock(inv.product_variant_id, owner_user_id=owner, quantity_to_add=3, idempotency_key=key)
    assert counters(db, inv) == (13, 0)
    assert db.query(InventoryRestock).filter_by(idempotency_key=key).count() == 1
    with pytest.raises(ConflictError):
        service.restock(inv.product_variant_id, owner_user_id=owner, quantity_to_add=4, idempotency_key=key)


def test_concurrent_restock_retry_is_applied_once(migration_database):
    from app.services.inventory_service import InventoryService
    from app.models.inventory_restock import InventoryRestock
    engine, config = migration_database
    migrate(engine, config, 'head')
    with Session(engine) as db:
        seller, _, _, variant, _ = catalog(db, stock=1)
        seller_id, variant_id = seller.id, variant.id
    key = uuid.uuid4().hex
    barrier = Barrier(2)
    def restock():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            InventoryService(db).restock(variant_id, owner_user_id=seller_id, quantity_to_add=5, idempotency_key=key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(restock) for _ in range(2)]
        for future in futures: future.result(timeout=20)
    with Session(engine) as db:
        inv = db.query(Inventory).filter_by(product_variant_id=variant_id).one()
        assert (inv.quantity_available, inv.quantity_reserved) == (6, 0)
        assert db.query(InventoryRestock).count() == 1
