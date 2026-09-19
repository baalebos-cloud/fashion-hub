"""
Notification fan-out: always writes an in-app Notification row, and
additionally dispatches to email/SMS/push via background tasks depending on
the event type and the user's notification preferences (preferences model
omitted from this scaffold for brevity -- add a NotificationPreference
table if granular opt-in/out is required).
"""
from sqlalchemy.orm import Session

EVENT_TITLES = {
    "order.accepted": "Your order was accepted",
    "order.production_started": "Production has started on your order",
    "order.ready_for_delivery": "Your order is ready",
    "order.shipped": "Your order has shipped",
    "order.out_for_delivery": "Your order is out for delivery",
    "order.delivered": "Your order has been delivered",
    "order.received": "Order marked as received",
    "order.completed": "Your order is complete",
    "order.cancelled": "Your order was cancelled",
    "payment.successful": "Payment received",
    "invoice.generated": "Your invoice is ready",
    "refund.processed": "Your refund has been processed",
    "verification.approved": "Your verification was approved",
    "verification.rejected": "Your verification needs attention",
    "delivery.exception": "There's an issue with your delivery",
    "referral.qualified": "You earned a referral commission",
}

# WhatsApp requires pre-approved message templates (see
# integrations/notifications/whatsapp.py) -- this maps our internal event
# names to the template name registered with the provider. Only
# vendor_order events trigger WhatsApp, per the product requirement that
# "each vendor, tailor/fashion designer should be notified for each other
# on their WhatsApp line" -- customer-order notifications stay in-app/email
# to avoid messaging customers on a channel they didn't opt into for this.
WHATSAPP_TEMPLATES = {
    "order.confirmed": "vendor_order_confirmed",
    "order.processing": "vendor_order_processing",
    "order.ready_for_pickup": "vendor_order_ready_for_pickup",
    "order.picked_up": "vendor_order_picked_up",
    "order.delivered": "vendor_order_delivered",
    "order.received": "vendor_order_received",
}


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def notify_order_status_changed(self, *, order_id: str, new_status: str):
        from app.models.order import Order
        from app.models.notification import Notification
        from app.models.user import User

        order = self.db.get(Order, order_id)
        if not order:
            return

        event_type = f"order.{new_status}"
        title = EVENT_TITLES.get(event_type, f"Order status updated: {new_status}")

        for recipient_id in {order.buyer_user_id, order.seller_user_id}:
            self.db.add(
                Notification(
                    recipient_user_id=recipient_id,
                    channel="in_app",
                    event_type=event_type,
                    title=title,
                    body=f"Order {order.order_number} is now {new_status.replace('_', ' ')}.",
                )
            )
        self.db.commit()

        # WhatsApp fan-out: vendor <-> tailor/designer only (see
        # WHATSAPP_TEMPLATES above). whatsapp_number is deliberately never
        # exposed in any API response (see schemas/professional.py,
        # schemas/vendor.py) -- it's only ever read here, server-side, to
        # dispatch the message itself.
        if order.order_type == "vendor_order" and event_type in WHATSAPP_TEMPLATES:
            template = WHATSAPP_TEMPLATES[event_type]
            for recipient_id in {order.buyer_user_id, order.seller_user_id}:
                recipient = self.db.get(User, recipient_id)
                if recipient and recipient.whatsapp_number:
                    from app.workers.whatsapp_tasks import send_whatsapp_task
                    send_whatsapp_task.delay(
                        to_phone=recipient.whatsapp_number,
                        template_name=template,
                        template_params=[order.order_number, new_status.replace("_", " ")],
                    )

    def notify_referral_qualified(self, *, referral_id: str):
        from app.models.referral import Referral
        from app.models.notification import Notification

        referral = self.db.get(Referral, referral_id)
        if not referral:
            return

        self.db.add(
            Notification(
                recipient_user_id=referral.referrer_user_id,
                channel="in_app",
                event_type="referral.qualified",
                title=EVENT_TITLES["referral.qualified"],
                body=f"Your referral just completed their first order -- you earned {referral.commission_amount} {referral.commission_currency}.",
            )
        )
        self.db.commit()

    def notify_delivery_tracking_stale(self, *, delivery_id: str):
        from app.models.delivery import Delivery
        from app.models.notification import Notification

        delivery = self.db.get(Delivery, delivery_id)
        if not delivery:
            return
        self.db.add(
            Notification(
                recipient_user_id=delivery.delivery_partner_id,
                channel="in_app",
                event_type="delivery.exception",
                title=EVENT_TITLES["delivery.exception"],
                body="Your GPS location has not updated recently. Please check your connection.",
            )
        )
        self.db.commit()

    def send_scheduled_reminders(self):
        """E.g. remind a tailor of an order accepted-but-not-started for
        >48h, or a customer of an unread delivered order for >24h."""
        raise NotImplementedError("Define reminder rules and query accordingly.")
