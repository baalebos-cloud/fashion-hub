"""
/admin

Admin-only operations: KYC/KYB review, dispute resolution, audit log browsing, platform configuration.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from typing import Literal

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from uuid import UUID
from app.core.timezone import utcnow
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.core.exceptions import NotFoundError, ValidationAppError
from app.services.commerce_dashboard_service import load_commerce_summary
from app.schemas.dispatch_board import DispatchBoardResponse

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
def list_users(
    role: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    """Paginated user list. Excludes passwords, NIN, and home location."""
    from sqlalchemy import func
    q = db.query(User).filter(User.is_active.is_(True))
    if role:
        q = q.filter(User.role == role)
    total = q.with_entities(func.count(User.id)).scalar()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_email_verified": u.is_email_verified,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/health-check")
def module_placeholder(current_user: User = Depends(require_roles(Role.ADMIN))):
    """Placeholder route confirming this module is wired into the app.
    Replace with real endpoints for Admin."""
    return {"module": "Admin", "status": "restricted"}


@router.get("/dispatch-board", response_model=DispatchBoardResponse)
def dispatch_board(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    """Read-only admin dispatch overview; customers and couriers cannot query it."""
    from app.models.delivery import Delivery
    from app.models.delivery_partner import DeliveryPartner
    from app.models.delivery_request import DeliveryRequest

    pending_query = db.query(DeliveryRequest).filter(DeliveryRequest.status == "requested")
    active_query = db.query(Delivery).filter(
        Delivery.status.in_(["assigned", "picked_up", "in_transit", "out_for_delivery"])
    )
    pending = pending_query.order_by(DeliveryRequest.created_at.desc()).limit(50).all()
    active = active_query.order_by(Delivery.created_at.desc()).limit(100).all()
    partner_ids = [d.delivery_partner_id for d in active if d.delivery_partner_id]
    partners = (db.query(DeliveryPartner).filter(DeliveryPartner.id.in_(partner_ids)).all()
                if partner_ids else [])
    by_id = {p.id: p for p in partners}
    return {
        "unassigned_count": pending_query.count(),
        "active_count": active_query.count(),
        "available_verified_riders": db.query(DeliveryPartner).filter(
            DeliveryPartner.is_verified.is_(True),
            DeliveryPartner.is_available.is_(True),
        ).count(),
        "pending": [
            {"id": p.id, "order_id": p.order_id, "status": p.status, "created_at": p.created_at}
            for p in pending
        ],
        "active": [
            {
                "id": d.id, "order_id": d.order_id, "status": d.status,
                "delivery_partner_id": d.delivery_partner_id,
                "vehicle_type": (by_id[d.delivery_partner_id].vehicle_type
                                 if d.delivery_partner_id in by_id else None),
                "created_at": d.created_at,
            }
            for d in active
        ],
    }


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
    from app.models.verification_document import VerificationDocument
    from app.core.config import settings
    from app.models.delivery_issue import DispatchIssueReport

    counts = dict(db.query(User.role, func.count(User.id))
                  .filter(User.is_active.is_(True)).group_by(User.role).all())
    ledger = dict(db.query(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount_minor), 0))
                  .group_by(LedgerEntry.direction).all())
    pending_kyc = db.query(KYCVerification).filter(KYCVerification.status.in_(("pending", "under_review"))).limit(50).all()
    pending_kyb = db.query(KYBVerification).filter(KYBVerification.status.in_(("pending", "under_review"))).limit(50).all()
    kyc_doc_ids = [x.id for x in pending_kyc]
    kyb_doc_ids = [x.id for x in pending_kyb]
    attached = db.query(VerificationDocument).filter(
        (VerificationDocument.kyc_verification_id.in_(kyc_doc_ids)) |
        (VerificationDocument.kyb_verification_id.in_(kyb_doc_ids))
    ).all()
    kyc_documents = {}
    kyb_documents = {}
    for doc in attached:
        if doc.kyc_verification_id:
            kyc_documents.setdefault(doc.kyc_verification_id, []).append(str(doc.id))
        if doc.kyb_verification_id:
            kyb_documents.setdefault(doc.kyb_verification_id, []).append(str(doc.id))
    issues = db.query(DispatchIssueReport).order_by(DispatchIssueReport.created_at.desc()).limit(20).all()
    recent_audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(20).all()
    return {
        "marketplace": {role: counts.get(role, 0) for role in
                        ("customer", "tailor", "designer", "vendor", "delivery_partner")},
        "verification": {
            "kyc_pending": [{"id": str(x.id), "user_id": str(x.user_id), "status": x.status, "documents": kyc_documents.get(x.id, [])} for x in pending_kyc],
            "kyb_pending": [{"id": str(x.id), "owner_id": str(x.business_owner_user_id), "status": x.status, "documents": kyb_documents.get(x.id, [])} for x in pending_kyb],
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


@router.get("/verifications")
def verification_queue(kind: Literal["kyc", "kyb"], db: Session = Depends(get_db),
                       admin: User = Depends(require_roles(Role.ADMIN))):
    """Open KYC or KYB submissions (pending or held for manual review), oldest first,
    with what the official registry confirmed. Never includes the raw NIN."""
    from app.services.verification_service import VerificationService
    return VerificationService(db).admin_queue(kind)


def _decide(kind, verification_id, payload, request, db, admin):
    from app.services.verification_service import VerificationService
    try:
        record = VerificationService(db).decide(kind=kind, verification_id=verification_id, admin=admin,
                                                approve=payload.approve, reason=payload.reason)
    except NotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValidationAppError as exc:
        raise HTTPException(422, str(exc)) from exc
    _audit(db, admin, request, f"{kind}.approved" if payload.approve else f"{kind}.rejected", record.id)
    db.commit()
    return {"id": str(record.id), "status": record.status}


@router.post("/kyc/{verification_id}/review")
def review_kyc(verification_id: UUID, payload: ReviewDecision, request: Request,
               db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    return _decide("kyc", verification_id, payload, request, db, admin)


@router.post("/kyb/{verification_id}/review")
def review_kyb(verification_id: UUID, payload: ReviewDecision, request: Request,
               db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    return _decide("kyb", verification_id, payload, request, db, admin)


@router.get("/verification-documents/{document_id}/preview")
def preview_verification_document(document_id: UUID, request: Request,
                                  db: Session = Depends(get_db),
                                  admin: User = Depends(require_roles(Role.ADMIN))):
    """Time-limited private preview; do not expose bucket keys in the API."""
    from app.models.verification_document import VerificationDocument
    from app.integrations.storage.object_storage import get_storage_provider
    document = db.get(VerificationDocument, document_id)
    if document is None or (document.kyc_verification_id is None and document.kyb_verification_id is None):
        raise HTTPException(404, "Verification document not found.")
    url = get_storage_provider().get_signed_url(document.storage_key, expires_in_seconds=120)
    _audit(db, admin, request, "verification.document_previewed", document.id)
    db.commit()
    return {"url": url, "expires_in_seconds": 120}


@router.get("/interswitch-sandbox/readiness")
def interswitch_sandbox_readiness(current_user: User = Depends(require_roles(Role.ADMIN))):
    """No credentials or payment data included; sandbox readiness only."""
    from app.services.interswitch_readiness import sandbox_readiness
    return sandbox_readiness()


@router.get("/verification-documents/{document_id}/content")
def fetch_verification_document_content(document_id: UUID, request: Request,
                                        db: Session = Depends(get_db),
                                        admin: User = Depends(require_roles(Role.ADMIN))):
    """Authenticated PostgreSQL private document stream, not a public URL."""
    from app.models.verification_document import VerificationDocument
    from app.models.stored_media import StoredMedia
    document = db.get(VerificationDocument, document_id)
    if document is None or (document.kyc_verification_id is None and document.kyb_verification_id is None):
        raise HTTPException(404, "Verification document not found.")
    media = db.query(StoredMedia).filter(StoredMedia.storage_key == document.storage_key).first()
    if media is None or media.is_public or not media.storage_key.startswith(("kyc/", "kyb/")):
        raise HTTPException(404, "Private document not found.")
    _audit(db, admin, request, "verification.document_previewed", document.id)
    db.commit()
    return Response(content=media.content, media_type=media.content_type,
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
