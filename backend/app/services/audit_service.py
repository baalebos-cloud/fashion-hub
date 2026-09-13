"""
Append-only audit logging. Call `record` from services performing
security-sensitive or business-critical actions (logins, role changes,
payment/refund decisions, verification approvals, admin-initiated order
changes). Never update or delete rows written through this service.
"""
from sqlalchemy.orm import Session


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(self, *, actor_user_id, action: str, resource_type: str | None = None, resource_id=None, ip_address: str | None = None, request_id: str | None = None, metadata: dict | None = None):
        from app.models.audit_log import AuditLog

        self.db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                request_id=request_id,
                metadata_json=metadata,
            )
        )
        self.db.commit()
