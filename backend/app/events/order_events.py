"""Handlers for order.* events (order.created, order.accepted, ...)."""
from app.events.publisher import subscribe


def _on_order_created(**payload):
    from app.core.database import session_scope
    from app.services.audit_service import AuditService

    with session_scope() as db:
        AuditService(db).record(actor_user_id=payload.get("actor_user_id"), action="order.created", resource_type="order", resource_id=payload.get("order_id"))


def register() -> None:
    subscribe("order.created", _on_order_created)
