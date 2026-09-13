"""
Wires event names to their handlers. Import and call `register_all()` once
at application startup (e.g. from app/main.py) so subscriptions are active
before any request is served.
"""
from app.events.publisher import subscribe


def register_all() -> None:
    from app.events import delivery_events, notification_events, order_events, payment_events, verification_events

    order_events.register()
    payment_events.register()
    delivery_events.register()
    verification_events.register()
    notification_events.register()
