"""Handlers for verification.* events (submitted, approved, rejected)."""
from app.events.publisher import subscribe


def _on_verification_approved(**payload):
    from app.core.database import session_scope
    from app.services.audit_service import AuditService

    with session_scope() as db:
        AuditService(db).record(actor_user_id=payload.get("reviewer_id"), action="verification.approved", resource_type=payload.get("resource_type"), resource_id=payload.get("resource_id"))


def register() -> None:
    subscribe("verification.approved", _on_verification_approved)
