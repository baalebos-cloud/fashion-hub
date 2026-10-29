"""
/admin

Admin-only operations: KYC/KYB review, dispute resolution, audit log browsing, platform configuration.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID
from app.core.timezone import utcnow
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.services.commerce_dashboard_service import load_commerce_summary

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health-check")
def module_placeholder(current_user: User = Depends(require_roles(Role.ADMIN))):
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Admin."""
    return {"module": "Admin", "status": "restricted"}


@router.get("/commerce-summary")
def commerce_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    """Admin-only real payment ledger aggregates; no customer records."""
    return load_commerce_summary(db)


@router.get("/operations")
def operations_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    """Admin-only counts and audit indicators, without exposing raw NIN or documents."""
    from sqlalchemy import func
    from app.models.kyc_verification import KYCVerification
    from app.models.kyb_verification import KYBVerification
    from app.models.saga import LedgerEntry
    from app.models.audit_log import AuditLog
    from app.core.config import settings
    from app.models.delivery_issue import DispatchIssueReport

    counts = dict(db.query(User.role, func.count(User.id))
                  .filter(User.is_active.is_(True)).group_by(User.role).all())
    ledger = dict(db.query(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount_minor), 0))
                  .group_by(LedgerEntry.direction).all())
    pending_kyc = db.query(KYCVerification).filter(KYCVerification.status == "pending").limit(50).all()
    pending_kyb = db.query(KYBVerification).filter(KYBVerification.status == "pending").limit(50).all()
    issues = db.query(DispatchIssueReport).order_by(DispatchIssueReport.created_at.desc()).limit(20).all()
    recent_audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(20).all()
    return {
        "marketplace": {role: counts.get(role, 0) for role in
                        ("customer", "tailor", "designer", "vendor", "delivery_partner")},
        "verification": {
            "kyc_pending": [{"id": str(x.id), "user_id": str(x.user_id), "status": x.status} for x in pending_kyc],
            "kyb_pending": [{"id": str(x.id), "owner_id": str(x.business_owner_user_id), "status": x.status} for x in pending_kyb],
        },
        "financial_controls": {
            "production_payments_enabled": settings.ENABLE_PRODUCTION_PAYMENTS,
            "ledger_debits_minor": int(ledger.get("debit", 0)),
            "ledger_credits_minor": int(ledger.get("credit", 0)),
            "ledger_balanced": ledger.get("debit", 0) == ledger.get("credit", 0),
        },
        "delivery_issues": [{"id": str(x.id), "delivery_id": str(x.delivery_id),
                             "type": x.issue_type, "status": x.status} for x in issues],
        "audit_events": [{"id": str(x.id), "action": x.action, "actor_id": str(x.actor_user_id) if x.actor_user_id else None} for x in recent_audits],
    }


class ReviewDecision(BaseModel):
    approve: bool
    reason: str | None = Field(None, max_length=1000)


def _audit(db, admin, request, action, resource_id):
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_user_id=admin.id, action=action, resource_type="verification",
                    resource_id=resource_id, ip_address=request.client.host if request.client else None,
                    metadata_json={"user_agent": request.headers.get("user-agent", "")[:300]}))


@router.post("/kyc/{verification_id}/review")
def review_kyc(verification_id: UUID, payload: ReviewDecision, request: Request,
               db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    from app.models.kyc_verification import KYCVerification
    record = db.query(KYCVerification).filter_by(id=verification_id, status="pending").with_for_update().first()
    if record is None:
        raise HTTPException(404, "Pending KYC verification not found.")
    if not payload.approve and not (payload.reason or "").strip():
        raise HTTPException(422, "Rejection reason is required.")
    if payload.approve and record.identity_match is False and not (payload.reason or "").strip():
        raise HTTPException(422, "A name mismatch requires an override reason.")
    record.status = "verified" if payload.approve else "rejected"
    record.rejection_reason = payload.reason
    record.reviewed_by_user_id = admin.id
    record.reviewed_at = utcnow()
    _audit(db, admin, request, "kyc.approved" if payload.approve else "kyc.rejected", record.id)
    db.commit()
    return {"id": str(record.id), "status": record.status}


@router.post("/kyb/{verification_id}/review")
def review_kyb(verification_id: UUID, payload: ReviewDecision, request: Request,
               db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    from app.models.kyb_verification import KYBVerification
    record = db.query(KYBVerification).filter_by(id=verification_id, status="pending").with_for_update().first()
    if record is None:
        raise HTTPException(404, "Pending KYB verification not found.")
    if not payload.approve and not (payload.reason or "").strip():
        raise HTTPException(422, "Rejection reason is required.")
    record.status = "verified" if payload.approve else "rejected"
    record.rejection_reason = payload.reason
    record.reviewed_by_user_id = admin.id
    record.reviewed_at = utcnow()
    _audit(db, admin, request, "kyb.approved" if payload.approve else "kyb.rejected", record.id)
    db.commit()
    return {"id": str(record.id), "status": record.status}
