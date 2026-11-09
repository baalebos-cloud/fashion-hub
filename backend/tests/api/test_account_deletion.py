"""Deleting your own account: refused while money or another person is waiting on it, otherwise
the person's details and personal data are erased and business records are kept."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.main import app
from app.models.address import Address
from app.models.audit_log import AuditLog
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.design import Design
from app.models.device_token import DeviceToken
from app.models.favorite import Favorite
from app.models.location import Location
from app.models.measurement import Measurement
from app.models.measurement_profile import MeasurementProfile
from app.models.notification import Notification
from app.models.order import Order
from app.models.payout import Payout
from app.models.professional import Professional
from app.models.user import RefreshSession, User
from app.services.account_deletion_service import DELETED_NAME

PASSWORD = "Password123"


@pytest.fixture()
def ctx(db, make_user):
    limiter.reset()
    current = [make_user(phone_number="+2348000000001", whatsapp_number="+2348000000001",
                         full_name="Ada Obi", profile_photo_url="https://cdn.example/ada.jpg")]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield dict(http=http, db=db, current=current, make_user=make_user)
    app.dependency_overrides.clear()


def _order(db, buyer, seller, status):
    order = Order(order_number="TL-" + uuid.uuid4().hex[:8].upper(), order_type="customer_order",
                  buyer_user_id=buyer.id, seller_user_id=seller.id, status=status,
                  subtotal=Decimal(100), total_amount=Decimal(100), currency="NGN")
    db.add(order)
    db.commit()
    return order


def _delete(http, password=PASSWORD):
    return http.request("DELETE", "/api/v1/users/me", json={"password": password})


def test_deleting_erases_personal_data_and_keeps_business_records(ctx):
    http, db, user = ctx["http"], ctx["db"], ctx["current"][0]
    tailor = ctx["make_user"](role="tailor")
    finished = _order(db, user, tailor, "completed")
    location = Location(location_type="address", formatted_address="12 Allen Avenue, Ikeja")
    db.add(location)
    db.flush()
    db.add(Address(user_id=user.id, location_id=location.id))
    profile = MeasurementProfile(customer_id=user.id, label="Me")
    db.add(profile)
    db.flush()
    db.add(Measurement(measurement_profile_id=profile.id, field_name="chest", value=Decimal(96)))
    db.add(Favorite(user_id=user.id, favorite_type="professional", favorite_ref_id=uuid.uuid4()))
    db.add(Notification(recipient_user_id=user.id, channel="in_app", event_type="order.accepted", title="Hi", body="Your order was accepted."))
    db.add(DeviceToken(user_id=user.id, platform="ios", token="apns-" + "a" * 64, last_seen_at=finished.created_at))
    db.add(RefreshSession(user_id=user.id, refresh_token_hash="x", expires_at=finished.created_at))
    db.commit()
    location_id, user_id, profile_id = location.id, user.id, profile.id

    assert http.get("/api/v1/users/me/deletion").json() == {"can_delete": True, "blockers": []}
    assert _delete(http).status_code == 204

    db.expire_all()
    gone = db.get(User, user_id)
    assert gone.is_active is False and gone.full_name == DELETED_NAME
    assert gone.email.startswith("deleted-") and gone.email.endswith("@deleted.invalid")
    assert gone.phone_number is None and gone.whatsapp_number is None and gone.profile_photo_url is None
    for model, column in [(Address, Address.user_id), (Favorite, Favorite.user_id),
                          (MeasurementProfile, MeasurementProfile.customer_id),
                          (Notification, Notification.recipient_user_id), (DeviceToken, DeviceToken.user_id)]:
        assert db.query(model).filter(column == user_id).count() == 0, model.__name__
    assert db.query(Measurement).filter(Measurement.measurement_profile_id == profile_id).count() == 0
    assert db.get(Location, location_id) is None
    assert all(s.revoked for s in db.query(RefreshSession).filter(RefreshSession.user_id == user_id))
    # The order stays for the tailor's and the business's records.
    order_id = finished.id
    assert db.get(Order, order_id).buyer_user_id == user_id
    assert db.query(AuditLog).filter(AuditLog.action == "account.deleted", AuditLog.resource_id == user_id).count() == 1


def test_old_password_and_email_no_longer_sign_in(ctx):
    http, db, user = ctx["http"], ctx["db"], ctx["current"][0]
    email = user.email
    assert _delete(http).status_code == 204
    app.dependency_overrides.pop(get_current_user)
    res = http.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 401


def test_wrong_password_changes_nothing(ctx):
    http, db, user = ctx["http"], ctx["db"], ctx["current"][0]
    assert _delete(http, "not-my-password").status_code == 403  # 401 would make the app retry
    db.expire_all()
    assert db.get(User, user.id).is_active is True and db.get(User, user.id).full_name == "Ada Obi"


@pytest.mark.parametrize("status", ["pending", "in_production", "out_for_delivery", "delivered"])
def test_open_orders_block_deletion(ctx, status):
    http, db, user = ctx["http"], ctx["db"], ctx["current"][0]
    _order(db, ctx["make_user"](), user, status)  # also counts when they're the seller
    check = http.get("/api/v1/users/me/deletion").json()
    assert check["can_delete"] is False and check["blockers"][0] == "You have 1 open order. Finish or cancel it first."
    res = _delete(http)
    assert res.status_code == 409 and "open order" in res.json()["error"]["message"]
    db.expire_all()
    assert db.get(User, user.id).is_active is True


def test_a_material_cart_does_not_block(ctx):
    http, db = ctx["http"], ctx["db"]
    tailor = ctx["make_user"](role="tailor")
    ctx["current"][0] = tailor
    order = Order(order_number="TL-" + uuid.uuid4().hex[:8].upper(), order_type="vendor_order", buyer_user_id=tailor.id,
                  seller_user_id=ctx["make_user"](role="vendor").id, status="cart", subtotal=Decimal(10),
                  total_amount=Decimal(10), currency="NGN")
    db.add(order)
    db.commit()
    assert http.get("/api/v1/users/me/deletion").json()["can_delete"] is True


def test_pending_payout_blocks_deletion(ctx):
    http, db = ctx["http"], ctx["db"]
    tailor = ctx["make_user"](role="tailor")
    ctx["current"][0] = tailor
    order = _order(db, ctx["make_user"](), tailor, "completed")
    db.add(Payout(order_id=order.id, seller_user_id=tailor.id, gross_amount=Decimal(100), commission_rate=Decimal("0.1"),
                  commission_amount=Decimal(10), net_amount=Decimal(90), status="pending"))
    db.commit()
    assert "paid out" in http.get("/api/v1/users/me/deletion").json()["blockers"][0]
    assert _delete(http).status_code == 409


def test_active_delivery_blocks_a_rider(ctx):
    http, db = ctx["http"], ctx["db"]
    rider = ctx["make_user"](role="delivery_partner")
    ctx["current"][0] = rider
    partner = DeliveryPartner(user_id=rider.id, vehicle_type="bike", is_verified=True, is_available=True)
    db.add(partner)
    db.flush()
    order = _order(db, ctx["make_user"](), ctx["make_user"](role="tailor"), "completed")
    db.add(Delivery(order_id=order.id, delivery_request_id=uuid.uuid4(), status="in_transit", provider="internal",
                    delivery_fee=0, delivery_partner_id=partner.id))
    db.commit()
    assert any("delivery in progress" in b for b in http.get("/api/v1/users/me/deletion").json()["blockers"])


def test_professional_listings_are_taken_down(ctx):
    http, db = ctx["http"], ctx["db"]
    tailor = ctx["make_user"](role="tailor")
    ctx["current"][0] = tailor
    pro = Professional(user_id=tailor.id, professional_type="tailor", business_name="Kemi Couture",
                       bio="Bespoke since 2010", is_verified=True)
    db.add(pro)
    db.flush()
    design = Design(professional_id=pro.id, title="Agbada", base_price=Decimal(50000), is_published=True)
    db.add(design)
    db.commit()
    assert _delete(http).status_code == 204
    db.expire_all()
    assert db.get(Design, design.id).is_published is False
    assert db.get(Professional, pro.id).accepts_new_orders is False and db.get(Professional, pro.id).bio is None


def test_admins_cannot_delete_from_the_app(ctx):
    http, db = ctx["http"], ctx["db"]
    ctx["current"][0] = ctx["make_user"](role="admin")
    assert http.get("/api/v1/users/me/deletion").json()["can_delete"] is False
    assert _delete(http).status_code == 403
