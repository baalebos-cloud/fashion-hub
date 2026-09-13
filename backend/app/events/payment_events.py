"""Handlers for payment.* events (payment.initialized, payment.successful, payment.failed)."""
from app.events.publisher import subscribe


def _on_payment_successful(**payload):
    from app.core.database import session_scope
    from app.services.audit_service import AuditService

    with session_scope() as db:
        AuditService(db).record(actor_user_id=None, action="payment.successful", resource_type="payment", resource_id=payload.get("payment_id"))


def register() -> None:
    subscribe("payment.successful", _on_payment_successful)
