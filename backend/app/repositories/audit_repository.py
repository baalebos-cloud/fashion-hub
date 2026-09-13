from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_recent(self, *, resource_type: str | None = None, offset: int = 0, limit: int = 50):
        query = self.db.query(AuditLog)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
