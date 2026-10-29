"""Sandbox checkout service security tests; no network calls or payment mutations."""
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, PaymentError
from app.services.interswitch_sandbox_service import InterswitchSandboxService


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "APP_URL", "https://backend.test.example")
    monkeypatch.setattr(settings, "INTERSWITCH_SANDBOX_ENABLED", True)
    monkeypatch.setattr(settings, "INTERSWITCH_MERCHANT_CODE", "MX_TEST")
    monkeypatch.setattr(settings, "INTERSWITCH_PAY_ITEM_ID", "ITEM_TEST")


def _service(order):
    service = object.__new__(InterswitchSandboxService)
    service.db = Mock()
    service.db.query.return_value.filter.return_value.first.return_value = None
    service.orders = Mock()
    service.orders.get_by_id.return_value = order
    service.orders.get_by_id_for_update.return_value = order
    return service


def _order():
    owner = uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(), buyer_user_id=owner, status="pending",
        total_amount=Decimal("125.50"), currency="NGN", order_type="customer_order",
    )


def test_sandbox_requires_explicit_flag(monkeypatch):
    monkeypatch.setattr(settings, "INTERSWITCH_SANDBOX_ENABLED", False)
    with pytest.raises(ConflictError):
        InterswitchSandboxService._require_sandbox()


def test_sandbox_never_runs_in_production(enabled, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(ConflictError):
        InterswitchSandboxService._require_sandbox()


def test_sandbox_requires_team_merchant_settings(enabled, monkeypatch):
    monkeypatch.setattr(settings, "INTERSWITCH_PAY_ITEM_ID", None)
    with pytest.raises(ConflictError):
        InterswitchSandboxService._require_sandbox()


def test_non_buyer_cannot_start_checkout(enabled):
    order = _order()
    service = _service(order)
    with pytest.raises(ForbiddenError):
        service.initialize_checkout(order_id=order.id, buyer_user_id=uuid.uuid4(),
                                    customer_email="owner@example.com")
    service.db.add.assert_not_called()


def test_wrong_currency_rejected_without_payment_creation(enabled):
    order = _order()
    order.currency = "USD"
    service = _service(order)
    with pytest.raises(ConflictError):
        service.initialize_checkout(order_id=order.id, buyer_user_id=order.buyer_user_id,
                                    customer_email="buyer@example.com")
    service.db.add.assert_not_called()


def test_checkout_stores_order_bound_reference_before_returning_form(enabled, monkeypatch):
    from app.services import catalog_order_service
    monkeypatch.setattr(catalog_order_service, "assert_catalog_order_payable", lambda order: None)
    order = _order()
    service = _service(order)
    result = service.initialize_checkout(order_id=order.id,
                                         buyer_user_id=order.buyer_user_id,
                                         customer_email="buyer@example.com")
    payment = service.db.add.call_args.args[0]
    assert payment.order_id == order.id
    assert payment.provider == "interswitch"
    assert payment.currency == "NGN"
    assert payment.status == "initialized"
    assert result.fields["txn_ref"] == payment.provider_reference
    assert result.fields["amount"] == "12550"
    assert result.fields["site_redirect_url"] == "https://backend.test.example/api/v1/interswitch/return"
    service.db.commit.assert_called_once()


def test_existing_other_provider_payment_never_reused(enabled):
    order = _order()
    service = _service(order)
    service.db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(provider="paystack")
    from app.services import catalog_order_service
    from unittest.mock import patch
    with patch.object(catalog_order_service, "assert_catalog_order_payable", return_value=None):
        with pytest.raises(PaymentError):
            service.initialize_checkout(order_id=order.id, buyer_user_id=order.buyer_user_id,
                                        customer_email="buyer@example.com")
    service.db.add.assert_not_called()


def test_customer_verification_requires_order_ownership(enabled):
    order = _order()
    service = _service(order)
    service._get_payment_by_reference = Mock(return_value=SimpleNamespace(
        provider="interswitch", order_id=order.id, amount=Decimal("125.50"),
    ))
    with pytest.raises(ForbiddenError):
        service.verify_and_confirm("seam_test", buyer_user_id=uuid.uuid4())
    service.db.commit.assert_not_called()


def test_browser_return_cannot_mark_an_order_paid():
    from app.api.v1.interswitch import browser_return
    redirect = browser_return(txnref="seam_test")
    assert redirect.status_code == 303
    assert "provider=interswitch" in redirect.headers["location"]
    assert "reference=seam_test" in redirect.headers["location"]


def test_material_order_can_initialize_in_sandbox_with_buyer_ownership(enabled):
    order = _order()
    order.order_type = "vendor_order"
    order.status = "checkout"
    order.pricing_source = "vendor_catalog_v1"
    order.delivery_address_snapshot = {"city": "Lagos"}
    order.items = [SimpleNamespace(quantity=1, unit_price=Decimal("125.50"), line_total=Decimal("125.50"))]
    order.subtotal = Decimal("125.50")
    order.delivery_fee = order.tax_amount = order.discount_amount = Decimal("0.00")
    service = _service(order)
    from app.services import catalog_order_service
    from unittest.mock import patch
    with patch.object(catalog_order_service, "assert_catalog_order_payable", return_value=None), \
         patch("app.services.stock_reservation_service.StockReservationService.active", return_value=True):
        result = service.initialize_checkout(order_id=order.id,
                                             buyer_user_id=order.buyer_user_id,
                                             customer_email="buyer@example.com")
    payment = service.db.add.call_args.args[0]
    assert payment.order_id == order.id
    assert payment.provider_reference.startswith("FH-MAT-")
    assert result.fields["txn_ref"] == payment.provider_reference
    assert result.fields["amount"] == "12550"
    service.db.commit.assert_called_once()


def test_material_order_cannot_be_paid_by_another_account(enabled):
    order = _order()
    order.order_type = "vendor_order"
    order.status = "checkout"
    service = _service(order)
    with pytest.raises(ForbiddenError):
        service.initialize_checkout(order_id=order.id,
                                    buyer_user_id=uuid.uuid4(),
                                    customer_email="stranger@example.com")
    service.db.add.assert_not_called()


def test_customer_checkout_uses_fashion_reference(enabled, monkeypatch):
    from app.services import catalog_order_service
    monkeypatch.setattr(catalog_order_service, "assert_catalog_order_payable", lambda order: None)
    order = _order()
    service = _service(order)
    service.initialize_checkout(order_id=order.id, buyer_user_id=order.buyer_user_id,
                                customer_email="buyer@example.com")
    assert service.db.add.call_args.args[0].provider_reference.startswith("FH-FAS-")


def test_authoritative_matching_success_reaches_settlement(enabled, monkeypatch):
    import app.services.interswitch_sandbox_service as mod
    order = _order()
    service = _service(order)
    payment = SimpleNamespace(provider="interswitch", order_id=order.id,
                              amount=Decimal("125.50"), currency="NGN",
                              provider_reference="seam_test")
    service._get_payment_by_reference = Mock(return_value=payment)
    settled = object()
    service._settle = Mock(return_value=settled)
    monkeypatch.setattr(mod, "requery_transaction", lambda **kwargs: SimpleNamespace(
        reference="seam_test", amount_minor=12550, currency="NGN", successful=True,
    ))
    assert service.verify_and_confirm("seam_test", buyer_user_id=order.buyer_user_id) is settled
    args, kwargs = service._settle.call_args
    assert args[1].status == "successful"
    assert args[1].amount == Decimal("125.50")
    assert args[-1] == order.buyer_user_id


def test_failed_provider_response_never_claims_success(enabled, monkeypatch):
    import app.services.interswitch_sandbox_service as mod
    order = _order()
    service = _service(order)
    payment = SimpleNamespace(provider="interswitch", order_id=order.id,
                              amount=Decimal("125.50"), currency="NGN",
                              provider_reference="seam_test")
    service._get_payment_by_reference = Mock(return_value=payment)
    service._settle = Mock(return_value=payment)
    monkeypatch.setattr(mod, "requery_transaction", lambda **kwargs: SimpleNamespace(
        reference="seam_test", amount_minor=12550, currency="NGN", successful=False,
    ))
    service.verify_and_confirm("seam_test", buyer_user_id=order.buyer_user_id)
    assert service._settle.call_args.args[1].status == "pending"


def test_mismatched_requery_reference_never_reaches_settlement(enabled, monkeypatch):
    import app.services.interswitch_sandbox_service as mod
    order = _order()
    service = _service(order)
    payment = SimpleNamespace(provider="interswitch", order_id=order.id,
                              amount=Decimal("125.50"), currency="NGN",
                              provider_reference="seam_test")
    service._get_payment_by_reference = Mock(return_value=payment)
    service._settle = Mock()
    monkeypatch.setattr(mod, "requery_transaction", lambda **kwargs: SimpleNamespace(
        reference="another_ref", amount_minor=12550, currency="NGN", successful=True,
    ))
    with pytest.raises(PaymentError):
        service.verify_and_confirm("seam_test", buyer_user_id=order.buyer_user_id)
    service._settle.assert_not_called()


def test_invalid_callback_reference_not_forwarded():
    from app.api.v1.interswitch import browser_return
    redirect = browser_return(txnref="../unsafe?code=00")
    assert "reference=" not in redirect.headers["location"]
    assert "provider=interswitch" in redirect.headers["location"]
