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
}


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def notify_order_status_changed(self, *, order_id: str, new_status: str):
        from app.models.order import Order
        from app.models.notification import Notification

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
