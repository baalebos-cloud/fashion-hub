"""Handlers for delivery.* events (delivery.created, delivery.picked_up, ...)."""
from app.events.publisher import subscribe


def _on_delivery_delivered(**payload):
    from app.core.database import session_scope
    from app.services.audit_service import AuditService

    with session_scope() as db:
        AuditService(db).record(actor_user_id=None, action="delivery.delivered", resource_type="delivery", resource_id=payload.get("delivery_id"))


def register() -> None:
    subscribe("delivery.delivered", _on_delivery_delivered)
