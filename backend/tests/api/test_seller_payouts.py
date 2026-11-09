"""Seller payouts: sent automatically once the customer confirms receipt, only to a checked bank account
whose name matches, never while a refund or delivery problem is open, and never twice."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.timezone import utcnow
from app.integrations.payments import paystack_transfers as paystack
from app.integrations.payments.paystack_transfers import TransferResult
from app.main import app
from app.models.audit_log import AuditLog
from app.models.kyc_verification import KYCVerification
from app.models.notification import Notification
from app.models.order import Order
from app.models.payout import Payout
from app.models.refund import Refund
from app.models.seller_bank_account import SellerBankAccount
from app.services.payout_release_service import PayoutReleaseService

BANKS = [{"code": "058", "name": "Guaranty Trust Bank"}, {"code": "044", "name": "Access Bank"}]


@pytest.fixture()
def ctx(db, make_user, monkeypatch):
    from app.core.rate_limit import limiter
    limiter.reset()  # adding a bank account is rate-limited like sign-in
    monkeypatch.setattr(settings, "IDENTITY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "PAYOUTS_ENABLED", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "paystack")
    monkeypatch.setattr(settings, "PAYMENT_SECRET_KEY", "sk_test_x")
    import app.services.seller_bank_account_service as banks_module
    monkeypatch.setattr(banks_module, "_banks_cache", BANKS)
    calls = {"transfers": [], "resolve": "ADA CHIOMA OBI", "transfer_status": "pending"}
    monkeypatch.setattr(paystack, "resolve_account", lambda number, code: calls["resolve"])
    monkeypatch.setattr(paystack, "create_recipient", lambda **kw: "RCP_" + kw["account_number"][-4:])

    def transfer(**kw):
        calls["transfers"].append(kw)
        return TransferResult(status=calls["transfer_status"], transfer_code="TRF_1")

    monkeypatch.setattr(paystack, "initiate_transfer", transfer)
    tailor = make_user(role="tailor", full_name="Ada Obi")
    db.add(KYCVerification(user_id=tailor.id, id_type="nin", status="verified", provider="prembly",
                           nin_verified_full_name="OBI ADA CHIOMA", nin_verified_date_of_birth=date(1990, 5, 17)))
    buyer = make_user(role="customer")
    db.commit()
    current = [tailor]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, tailor=tailor, buyer=buyer, calls=calls, current=current, make_user=make_user)
    app.dependency_overrides.clear()


def _add_account(ctx, password="Password123"):
    res = ctx["http"].put("/api/v1/payments/payout-account",
                           json={"bank_code": "058", "account_number": "0123456789", "password": password})
    assert res.status_code != 429
    return res


def _paid_order(ctx, status="received", amount=10_000):
    db = ctx["db"]
    order = Order(order_number="TL-" + uuid.uuid4().hex[:8].upper(), order_type="customer_order",
                  buyer_user_id=ctx["buyer"].id, seller_user_id=ctx["tailor"].id, status=status,
                  subtotal=Decimal(amount), total_amount=Decimal(amount), currency="NGN")
    db.add(order)
    db.flush()
    payout = Payout(order_id=order.id, seller_user_id=ctx["tailor"].id, gross_amount=Decimal(amount),
                    commission_rate=Decimal("0.15"), commission_amount=Decimal(amount) * Decimal("0.15"),
                    net_amount=Decimal(amount) * Decimal("0.85"), currency="NGN", status="pending")
    db.add(payout)
    db.commit()
    return order, payout


# ---- bank account ---------------------------------------------------------------------------------
def test_adding_a_bank_account_checks_it_and_needs_the_password(ctx):
    assert _add_account(ctx, password="wrong").status_code == 403
    res = _add_account(ctx)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body == {**body, "bank_name": "Guaranty Trust Bank", "account_last4": "6789",
                    "account_name": "ADA CHIOMA OBI", "name_matches": True}
    account = ctx["db"].query(SellerBankAccount).filter_by(user_id=ctx["tailor"].id).one()
    assert "0123456789" not in account.account_number_encrypted and account.recipient_code == "RCP_6789"
    assert ctx["db"].query(Notification).filter_by(recipient_user_id=ctx["tailor"].id,
                                                   event_type="payout.account_changed").count() == 1
    assert ctx["http"].get("/api/v1/payments/payout-account").json()["account"]["account_last4"] == "6789"


def test_someone_elses_account_is_flagged(ctx):
    ctx["calls"]["resolve"] = "TUNDE BAKARE"
    assert _add_account(ctx).json()["name_matches"] is False


def test_customers_cant_add_payout_accounts(ctx):
    ctx["current"][0] = ctx["buyer"]
    assert _add_account(ctx).status_code == 403


# ---- sending ----------------------------------------------------------------------------------------
def test_received_order_is_paid_automatically_then_confirmed_by_paystack(ctx):
    _add_account(ctx)
    order, payout = _paid_order(ctx)
    service = PayoutReleaseService(ctx["db"])
    assert service.release_ready() == {"sent": 1, "held": 0, "failed": 0}
    sent = ctx["calls"]["transfers"][0]
    assert sent["amount_kobo"] == 850_000 and sent["recipient_code"] == "RCP_6789"
    ctx["db"].refresh(payout)
    assert payout.status == "processing" and payout.transfer_reference == sent["reference"]
    assert service.release_ready()["sent"] == 0  # never sent twice
    assert service.record_transfer_event(event="transfer.success", data={"reference": payout.transfer_reference})
    ctx["db"].refresh(payout)
    assert payout.status == "paid" and payout.released_at is not None
    assert ctx["db"].query(Notification).filter_by(recipient_user_id=ctx["tailor"].id, title="Payout sent").count() == 1
    assert service.record_transfer_event(event="transfer.success", data={"reference": payout.transfer_reference})
    assert ctx["db"].query(Notification).filter_by(recipient_user_id=ctx["tailor"].id, title="Payout sent").count() == 1


def test_nothing_is_sent_before_receipt_or_while_switched_off(ctx, monkeypatch):
    _add_account(ctx)
    _, waiting = _paid_order(ctx, status="delivered")
    service = PayoutReleaseService(ctx["db"])
    assert service.release_ready()["sent"] == 0
    _paid_order(ctx)
    monkeypatch.setattr(settings, "PAYOUTS_ENABLED", False)
    assert service.release_ready() == {"sent": 0, "held": 0, "failed": 0}
    assert ctx["calls"]["transfers"] == []


@pytest.mark.parametrize("setup, words", [
    ("refund", "refund"),
    ("no_account", "bank account"),
    ("name_mismatch", "doesn't match"),
])
def test_blocked_payouts_are_held_with_the_reason(ctx, setup, words):
    if setup == "name_mismatch":
        ctx["calls"]["resolve"] = "TUNDE BAKARE"
    if setup != "no_account":
        _add_account(ctx)
    order, payout = _paid_order(ctx)
    if setup == "refund":
        ctx["db"].add(Refund(payment_id=uuid.uuid4(), order_id=order.id, requested_by_user_id=ctx["buyer"].id,
                             amount=Decimal(100), status="requested"))
        ctx["db"].commit()
    assert PayoutReleaseService(ctx["db"]).release_ready()["held"] == 1
    ctx["db"].refresh(payout)
    assert payout.status == "held" and words in payout.hold_reason
    assert ctx["calls"]["transfers"] == []


def test_failures_are_recorded_and_an_admin_can_retry(ctx, monkeypatch):
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    ctx["calls"]["transfer_status"] = "otp"
    service = PayoutReleaseService(ctx["db"])
    assert service.release_ready()["failed"] == 1
    ctx["db"].refresh(payout)
    assert payout.status == "failed" and "OTP" in payout.failure_reason
    admin = ctx["make_user"](role="admin")
    # Before retrying, Paystack confirms the last attempt really failed.
    monkeypatch.setattr(paystack, "verify_transfer", lambda ref: TransferResult(status="failed", transfer_code=None))
    service.release(payout.id, admin=admin)
    ctx["calls"]["transfer_status"] = "pending"
    assert service.release_ready()["sent"] == 1
    refs = [t["reference"] for t in ctx["calls"]["transfers"]]
    assert len(set(refs)) == 2  # a fresh reference per attempt


def test_a_missed_webhook_is_caught_by_checking_with_paystack(ctx, monkeypatch):
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    service = PayoutReleaseService(ctx["db"])
    service.release_ready()
    payout.processing_at = utcnow() - timedelta(hours=2)
    ctx["db"].commit()
    monkeypatch.setattr(paystack, "verify_transfer", lambda ref: TransferResult(status="success", transfer_code="TRF_1"))
    assert service.reconcile_processing() == 1
    ctx["db"].refresh(payout)
    assert payout.status == "paid"


# ---- admins -----------------------------------------------------------------------------------------
def test_admin_hold_and_release_need_the_authenticator_for_release(ctx, monkeypatch):
    ctx["calls"]["resolve"] = "TUNDE BAKARE"
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    PayoutReleaseService(ctx["db"]).release_ready()  # held: name doesn't match
    admin = ctx["make_user"](role="admin")
    ctx["current"][0] = admin
    listing = ctx["http"].get("/api/v1/admin/payouts?status=held").json()
    assert listing["payouts_enabled"] is True and listing["items"][0]["hold_reason"]
    assert ctx["http"].post(f"/api/v1/admin/payouts/{payout.id}/release").status_code == 403  # no code
    from app.services.admin_auth_service import AdminStepUpService
    monkeypatch.setattr(AdminStepUpService, "require", lambda self, **_: None)
    assert ctx["http"].post(f"/api/v1/admin/payouts/{payout.id}/release").json()["status"] == "pending"
    # An admin release also confirms the bank account by hand, so the next run sends it.
    assert PayoutReleaseService(ctx["db"]).release_ready()["sent"] == 1
    assert ctx["db"].query(AuditLog).filter_by(action="payout.released_by_admin", resource_id=payout.id).count() == 1
    other_order, other = _paid_order(ctx, status="delivered")
    assert ctx["http"].post(f"/api/v1/admin/payouts/{other.id}/hold", json={"reason": "Customer complaint"}).json()["status"] == "held"


def test_sellers_see_hold_reasons_on_their_payouts(ctx):
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    payout.status, payout.hold_reason = "held", "A refund on this order is open or done."
    ctx["db"].commit()
    rows = ctx["http"].get("/api/v1/payments/payouts").json()
    assert rows[0]["status"] == "held" and "refund" in rows[0]["hold_reason"]


def test_paystack_transfer_webhook_marks_the_payout_paid(ctx):
    import hashlib
    import hmac
    import json as _json
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    PayoutReleaseService(ctx["db"]).release_ready()
    ctx["db"].refresh(payout)
    raw = _json.dumps({"event": "transfer.success", "data": {"reference": payout.transfer_reference}}).encode()
    signature = hmac.new(b"sk_test_x", raw, hashlib.sha512).hexdigest()
    bad = ctx["http"].post("/api/v1/payments/webhooks/paystack", content=raw, headers={"x-paystack-signature": "nope"})
    assert bad.status_code == 401
    res = ctx["http"].post("/api/v1/payments/webhooks/paystack", content=raw, headers={"x-paystack-signature": signature})
    assert res.status_code == 200 and res.json()["reconciled"] is True
    ctx["db"].refresh(payout)
    assert payout.status == "paid"



# ---- review fixes ------------------------------------------------------------------------------------
def test_no_answer_from_paystack_is_never_treated_as_failed(ctx, monkeypatch):
    _add_account(ctx)
    _, payout = _paid_order(ctx)

    def timeout(**kw):
        ctx["calls"]["transfers"].append(kw)
        raise paystack.TransferOutcomeUnknown("Paystack didn't answer in time.")

    monkeypatch.setattr(paystack, "initiate_transfer", timeout)
    service = PayoutReleaseService(ctx["db"])
    service.release_ready()
    ctx["db"].refresh(payout)
    assert payout.status == "processing"  # may have gone through: wait for Paystack
    admin = ctx["make_user"](role="admin")
    with pytest.raises(Exception):
        service.release(payout.id, admin=admin)  # can't start a new attempt while one may be in flight
    first = payout.transfer_reference
    # A late success for that attempt still marks it paid.
    assert service.record_transfer_event(event="transfer.success", data={"reference": first})
    ctx["db"].refresh(payout)
    assert payout.status == "paid" and len(ctx["calls"]["transfers"]) == 1


def test_a_retry_that_already_went_through_is_not_sent_again(ctx, monkeypatch):
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    ctx["calls"]["transfer_status"] = "failed"
    service = PayoutReleaseService(ctx["db"])
    service.release_ready()
    monkeypatch.setattr(paystack, "verify_transfer", lambda ref: TransferResult(status="success", transfer_code="T"))
    service.release(payout.id, admin=ctx["make_user"](role="admin"))
    ctx["db"].refresh(payout)
    assert payout.status == "paid" and len(ctx["calls"]["transfers"]) == 1


@pytest.mark.parametrize("state", ["manual_review", "needs_attention"])
def test_unresolved_refund_states_hold_the_payout(ctx, state):
    _add_account(ctx)
    order, payout = _paid_order(ctx)
    ctx["db"].add(Refund(payment_id=uuid.uuid4(), order_id=order.id, requested_by_user_id=ctx["buyer"].id,
                         amount=Decimal(100), status=state))
    ctx["db"].commit()
    assert PayoutReleaseService(ctx["db"]).release_ready()["held"] == 1


def test_only_a_verified_business_name_counts(ctx):
    from app.models.kyb_verification import KYBVerification
    from app.models.professional import Professional
    ctx["calls"]["resolve"] = "LACE WORLD LIMITED"
    ctx["db"].add(Professional(user_id=ctx["tailor"].id, professional_type="tailor", business_name="Lace World Limited"))
    ctx["db"].commit()
    assert _add_account(ctx).json()["name_matches"] is False  # self-typed business name isn't proof
    ctx["db"].add(KYBVerification(business_owner_user_id=ctx["tailor"].id, business_registration_number="1234567",
                                  company_type="RC", provider="prembly", verified_company_name="LACE WORLD LIMITED",
                                  name_match=True, status="verified"))
    ctx["db"].commit()
    from app.core.rate_limit import limiter
    limiter.reset()
    assert _add_account(ctx).json()["name_matches"] is True


def test_a_reversal_after_payment_makes_it_owed_again(ctx):
    _add_account(ctx)
    _, payout = _paid_order(ctx)
    service = PayoutReleaseService(ctx["db"])
    service.release_ready()
    ref = payout.transfer_reference
    service.record_transfer_event(event="transfer.success", data={"reference": ref})
    service.record_transfer_event(event="transfer.reversed", data={"reference": ref})
    ctx["db"].refresh(payout)
    assert payout.status == "failed" and payout.released_at is None and "after it was paid" in payout.failure_reason
    assert ctx["db"].query(Notification).filter_by(recipient_user_id=ctx["tailor"].id, title="Payout returned").count() == 1


def test_paystack_answers_are_sorted_into_refused_unknown_or_not_found(monkeypatch):
    import httpx
    from app.core.exceptions import ExternalProviderError
    monkeypatch.setattr(settings, "PAYMENT_SECRET_KEY", "sk_test_x")

    class Reply:
        def __init__(self, status, body):
            self.status_code, self._body = status, body

        def json(self):
            return self._body

    def client(reply=None, error=None):
        class C:
            def post(self, *a, **k):
                if error:
                    raise error
                return reply
            get = post
        return C()

    args = dict(amount_kobo=100, recipient_code="R", reference="payout-x-1", reason="r")
    with pytest.raises(paystack.TransferOutcomeUnknown):
        paystack.initiate_transfer(**args, client=client(error=httpx.ReadTimeout("slow")))
    with pytest.raises(paystack.TransferOutcomeUnknown):
        paystack.initiate_transfer(**args, client=client(Reply(502, {})))
    with pytest.raises(paystack.TransferNotFound):
        paystack.verify_transfer("payout-x-1", client=client(Reply(404, {"status": False})))
    with pytest.raises(ExternalProviderError) as refused:
        paystack.initiate_transfer(**args, client=client(Reply(400, {"status": False, "message": "Insufficient balance"})))
    assert not isinstance(refused.value, paystack.TransferOutcomeUnknown) and "Insufficient balance" in str(refused.value)
