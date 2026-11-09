"""Deleting your own account (App Store Guideline 5.1.1(v), Google Play account deletion).

Deleting is refused while anything involving money or another person is still in progress (an open
order, an active delivery, a payout not yet released, a refund still being decided), so nothing is
left half-done. Otherwise, in one transaction:

- the account is switched off and signed out everywhere, and its phones stop getting notifications;
- the person's details (name, email, phone, WhatsApp, photo) are replaced with "Deleted user";
- personal data is erased: addresses, measurements, favourites, cart, AI chats, notifications and
  recorded activity; a professional's or vendor's listings are taken down;
- records the business has to keep (orders, payments, invoices, receipts, payouts, refunds and identity
  checks) stay, now showing "Deleted user" instead of the person's details. Messages and reviews stay
  readable for the other person, under "Deleted user".
"""
from __future__ import annotations

import logging
import secrets

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError
from app.core.security import hash_password, verify_password
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage
from app.models.address import Address
from app.models.audit_log import AuditLog
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.design import Design
from app.models.device_token import DeviceToken
from app.models.favorite import Favorite
from app.models.interaction_event import InteractionEvent
from app.models.location import Location
from app.models.measurement import Measurement
from app.models.measurement_profile import MeasurementProfile
from app.models.notification import Notification
from app.models.order import Order
from app.models.payout import Payout
from app.models.professional import Professional
from app.models.recommendation_impression import RecommendationImpression
from app.models.refund import Refund
from app.integrations.storage.object_storage import get_storage_provider
from app.models.storefront_handle import StorefrontHandle
from app.models.stored_media import StoredMedia
from app.models.user import RefreshSession, User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.services.masked_call_service import ACTIVE_DELIVERY_STATUSES, CLOSED_ORDER_STATUSES

logger = logging.getLogger(__name__)

DELETED_NAME = "Deleted user"
# A material order still being put together in the cart: nothing bought, nobody waiting on it.
# ("checkout" is not here: its payment page may still be paid, so it blocks like any open order.)
NOT_YET_ORDERED = {"cart"}
# Kept from a past order's delivery address: enough for tax and statistics, not enough to find anyone.
KEPT_ADDRESS_FIELDS = ("city", "state_region", "country")


def deleted_email(user_id) -> str:
    return f"deleted-{user_id}@deleted.invalid"


class AccountDeletionService:
    def __init__(self, db: Session):
        self.db = db

    def blockers(self, user: User) -> list[str]:
        """What has to finish first, in words the person can act on. Empty means they can delete."""
        if user.role == "admin":
            return ["Admin accounts can't be deleted from the app. Ask another admin to remove the account."]
        reasons: list[str] = []
        open_orders = (self.db.query(Order)
                       .filter(or_(Order.buyer_user_id == user.id, Order.seller_user_id == user.id),
                               Order.status.notin_(CLOSED_ORDER_STATUSES | NOT_YET_ORDERED)).count())
        if open_orders:
            one = open_orders == 1
            reasons.append(f"You have {open_orders} open order{'' if one else 's'}. "
                           f"Finish or cancel {'it' if one else 'them'} first.")
        partner = self.db.query(DeliveryPartner).filter(DeliveryPartner.user_id == user.id).first()
        if partner and (self.db.query(Delivery)
                        .filter(Delivery.delivery_partner_id == partner.id,
                                Delivery.status.in_(ACTIVE_DELIVERY_STATUSES)).count()):
            reasons.append("You have a delivery in progress. Complete it first.")
        if self.db.query(Payout).filter(Payout.seller_user_id == user.id, Payout.status == "pending").count():
            reasons.append("You have money waiting to be paid out to you. Wait until it has been paid.")
        order_ids = self.db.query(Order.id).filter(
            or_(Order.buyer_user_id == user.id, Order.seller_user_id == user.id))
        if (self.db.query(Refund)
                .filter(Refund.status == "requested",
                        or_(Refund.requested_by_user_id == user.id, Refund.order_id.in_(order_ids))).count()):
            reasons.append("A refund on one of your orders is still being decided. Wait for the outcome.")
        return reasons

    def delete(self, user: User, *, password: str) -> None:
        if not verify_password(password, user.hashed_password):
            # 403, not 401: a 401 makes the app refresh the session and send the request again.
            raise ForbiddenError("That password isn't right.")
        # One deletion at a time per account, and nothing new can start on it while this runs.
        user = self.db.query(User).filter(User.id == user.id).with_for_update().one()
        if user.role == "admin":
            raise ForbiddenError(self.blockers(user)[0])
        reasons = self.blockers(user)
        if reasons:
            raise ConflictError(" ".join(reasons))

        uid = user.id
        q = self.db.query

        # Signed out everywhere, no more notifications to their phones.
        q(RefreshSession).filter(RefreshSession.user_id == uid).update({"revoked": True}, synchronize_session=False)
        q(DeviceToken).filter(DeviceToken.user_id == uid).delete(synchronize_session=False)

        # Personal data that only matters to them.
        location_ids = [row.location_id for row in q(Address.location_id).filter(Address.user_id == uid)]
        q(Address).filter(Address.user_id == uid).delete(synchronize_session=False)
        for location_id in location_ids:
            # The saved place goes too, unless a past delivery still points at it.
            try:
                with self.db.begin_nested():
                    q(Location).filter(Location.id == location_id).delete(synchronize_session=False)
            except IntegrityError:
                pass
        q(Customer).filter(Customer.user_id == uid).update({"default_measurement_profile_id": None},
                                                           synchronize_session=False)
        profile_ids = [row.id for row in q(MeasurementProfile.id).filter(MeasurementProfile.customer_id == uid)]
        if profile_ids:
            q(Measurement).filter(Measurement.measurement_profile_id.in_(profile_ids)).delete(synchronize_session=False)
            q(MeasurementProfile).filter(MeasurementProfile.id.in_(profile_ids)).delete(synchronize_session=False)
        q(Favorite).filter(Favorite.user_id == uid).delete(synchronize_session=False)
        cart_ids = [row.id for row in q(Cart.id).filter(Cart.owner_user_id == uid)]
        if cart_ids:
            # Carts that became orders stay linked to them; only their contents go.
            q(CartItem).filter(CartItem.cart_id.in_(cart_ids)).delete(synchronize_session=False)
            q(Cart).filter(Cart.id.in_(cart_ids), Cart.status == "active").update(
                {"status": "abandoned"}, synchronize_session=False)
        conversation_ids = [row.id for row in q(AIConversation.id).filter(AIConversation.user_id == uid)]
        if conversation_ids:
            q(AIMessage).filter(AIMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            q(AIConversation).filter(AIConversation.id.in_(conversation_ids)).delete(synchronize_session=False)
        q(Notification).filter(Notification.recipient_user_id == uid).delete(synchronize_session=False)
        q(InteractionEvent).filter(InteractionEvent.user_id == uid).delete(synchronize_session=False)
        q(RecommendationImpression).filter(RecommendationImpression.user_id == uid).delete(synchronize_session=False)

        # Copies saved on their past orders: keep only the area of the delivery address, drop the
        # recipient's name, phone, street and map point, and the body measurements.
        for order in q(Order).filter(Order.buyer_user_id == uid):
            snapshot = order.delivery_address_snapshot
            if snapshot:
                order.delivery_address_snapshot = {k: snapshot.get(k) for k in KEPT_ADDRESS_FIELDS if snapshot.get(k)}
            order.measurement_snapshot = None

        # Uploaded profile photos stop being reachable at their old links.
        avatar_prefix = f"avatar/{uid}/"
        q(StoredMedia).filter(StoredMedia.owner_user_id == uid, StoredMedia.storage_key.like("avatar/%")).delete(
            synchronize_session=False)
        photo_url = user.profile_photo_url or ""
        external_avatar = (photo_url[photo_url.index(avatar_prefix):].split("?")[0]
                           if avatar_prefix in photo_url else None)

        # Take down anything they were offering to others.
        professional = q(Professional).filter(Professional.user_id == uid).first()
        if professional:
            professional.accepts_new_orders = False
            professional.bio = None
            q(Design).filter(Design.professional_id == professional.id).update(
                {"is_published": False}, synchronize_session=False)
        vendor = q(Vendor).filter(Vendor.user_id == uid).first()
        if vendor:
            q(VendorProduct).filter(VendorProduct.vendor_id == vendor.id).update(
                {"is_active": False}, synchronize_session=False)
        q(DeliveryPartner).filter(DeliveryPartner.user_id == uid).update(
            {"is_available": False}, synchronize_session=False)
        q(StorefrontHandle).filter(StorefrontHandle.owner_user_id == uid).delete(synchronize_session=False)

        # The account itself: switched off, and nothing left that identifies the person.
        user.is_active = False
        user.full_name = DELETED_NAME
        user.email = deleted_email(uid)
        user.phone_number = None
        user.whatsapp_number = None
        user.profile_photo_url = None
        user.referral_code = None
        user.home_location_id = None
        user.is_email_verified = False
        user.is_phone_verified = False
        user.personalization_enabled = False
        user.hashed_password = hash_password(secrets.token_urlsafe(32))  # nobody knows it: can't sign in

        self.db.add(AuditLog(actor_user_id=uid, action="account.deleted", resource_type="user", resource_id=uid))
        self.db.commit()

        if external_avatar and settings.STORAGE_PROVIDER not in {"postgres"}:
            # Photos kept outside the database (object storage): removed once the account is gone.
            try:
                get_storage_provider().delete(external_avatar)
            except Exception:  # noqa: BLE001 - the account is deleted either way; the key is logged, not the URL
                logger.warning("account_deleted_avatar_not_removed user=%s", uid)
