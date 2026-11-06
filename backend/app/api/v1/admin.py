"""
/admin

Admin-only operations: KYC/KYB review, dispute resolution, audit log browsing, platform configuration.

STATUS: scaffold stub. Wire in the corresponding service (see
app/services/) and repository as this module is implemented; follow the
pattern established in auth.py / orders.py (RBAC via require_roles,
business rules delegated to a service, never inline in the route).
"""
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from uuid import UUID
from app.core.timezone import utcnow
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.core.exceptions import NotFoundError, ValidationAppError
from app.services.commerce_dashboard_service import load_commerce_summary
from app.schemas.dispatch_board import DispatchActionReason, DispatchBoardResponse, IssueUpdateRequest, ReassignRequest

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
    from app.models.order import Order
    from app.services.dispatch_admin_service import DispatchAdminService, _first_name
    orders = {o.id: o for o in db.query(Order).filter(
        Order.id.in_({p.order_id for p in pending} | {d.order_id for d in active})).all()} if (pending or active) else {}
    partner_ids = [d.delivery_partner_id for d in active if d.delivery_partner_id]
    partners = (db.query(DeliveryPartner, User).join(User, User.id == DeliveryPartner.user_id)
                .filter(DeliveryPartner.id.in_(partner_ids)).all() if partner_ids else [])
    by_id = {p.id: (p, u) for p, u in partners}
    service = DispatchAdminService(db)
    issue_counts = service.open_issue_counts([d.id for d in active])
    from app.services.auto_dispatch_service import AutoDispatchService, auto_offers_enabled
    offer_status = AutoDispatchService(db).admin_status([p.id for p in pending]) if auto_offers_enabled() else {}
    from app.models.delivery_issue import DispatchIssueReport
    return {
        "unassigned_count": pending_query.count(),
        "active_count": active_query.count(),
        "available_verified_riders": db.query(DeliveryPartner).filter(
            DeliveryPartner.is_verified.is_(True),
            DeliveryPartner.is_available.is_(True),
        ).count(),
        "auto_offers_enabled": auto_offers_enabled(),
        "open_issue_count": db.query(DispatchIssueReport).filter(
            DispatchIssueReport.status.notin_(("RESOLVED", "REROUTED"))).count(),
        "pending": [
            {"id": p.id, "order_id": p.order_id, "status": p.status, "created_at": p.created_at,
             "order_number": orders[p.order_id].order_number if p.order_id in orders else None,
             "order_type": orders[p.order_id].order_type if p.order_id in orders else None,
             **offer_status.get(p.id, {})}
            for p in pending
        ],
        "active": [
            {
                "id": d.id, "order_id": d.order_id, "status": d.status,
                "order_number": orders[d.order_id].order_number if d.order_id in orders else None,
                "order_type": orders[d.order_id].order_type if d.order_id in orders else None,
                "delivery_partner_id": d.delivery_partner_id,
                "rider_first_name": _first_name(by_id[d.delivery_partner_id][1]) if d.delivery_partner_id in by_id else None,
                "vehicle_type": by_id[d.delivery_partner_id][0].vehicle_type if d.delivery_partner_id in by_id else None,
                "open_issue_count": int(issue_counts.get(d.id, 0)),
                "created_at": d.created_at,
                "tracking": _tracking(d),
            }
            for d in active
        ],
    }


def _tracking(delivery):
    if delivery.status != "in_transit":
        return None
    from app.services.delivery_position import tracking_status
    return tracking_status(delivery.id)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/dispatch/riders")
def dispatch_available_riders(db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Verified riders who are online, for dispatcher reassignment. First names only."""
    from app.services.dispatch_admin_service import DispatchAdminService
    return DispatchAdminService(db).available_riders()


@router.post("/dispatch/deliveries/{delivery_id}/release")
def dispatch_release(delivery_id: UUID, payload: DispatchActionReason, request: Request,
                     db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Take a not-yet-collected job from its rider and put it back on the job board."""
    from app.services.dispatch_admin_service import DispatchAdminService
    fresh = DispatchAdminService(db).release(delivery_id=delivery_id, admin=admin,
                                             reason=payload.reason, ip=_client_ip(request))
    return {"request_id": str(fresh.id), "status": fresh.status}


@router.post("/dispatch/deliveries/{delivery_id}/reassign")
def dispatch_reassign(delivery_id: UUID, payload: ReassignRequest, request: Request,
                      db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Move a not-yet-collected job to a chosen verified, online rider."""
    from app.services.dispatch_admin_service import DispatchAdminService
    delivery = DispatchAdminService(db).reassign(delivery_id=delivery_id, partner_id=payload.partner_id,
                                                 admin=admin, reason=payload.reason, ip=_client_ip(request))
    return {"delivery_id": str(delivery.id), "status": delivery.status}


@router.post("/dispatch/requests/{request_id}/cancel")
def dispatch_cancel_request(request_id: UUID, payload: DispatchActionReason, request: Request,
                            db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Stop the rider search for an order; the seller can request again later."""
    from app.services.dispatch_admin_service import DispatchAdminService
    record = DispatchAdminService(db).cancel_request(request_id=request_id, admin=admin,
                                                     reason=payload.reason, ip=_client_ip(request))
    return {"request_id": str(record.id), "status": record.status}


@router.get("/dispatch/deliveries/{delivery_id}/events")
def dispatch_delivery_events(delivery_id: UUID, db: Session = Depends(get_db),
                             admin: User = Depends(require_roles(Role.ADMIN))):
    """A run's audit trail: codes issued, failed checks, pickup and drop-off. Never the codes."""
    from app.services.internal_courier_service import InternalCourierService
    return [{"id": str(e.id), "event_type": e.event_type, "actor_role": e.actor_role,
             "details": e.details or {}, "created_at": e.created_at}
            for e in InternalCourierService(db).events(delivery_id=delivery_id, actor=admin)]


@router.get("/dispatch/issues")
def dispatch_open_issues(db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Rider-reported problems that aren't resolved yet, oldest first."""
    from app.services.dispatch_admin_service import DispatchAdminService
    return DispatchAdminService(db).open_issues()


@router.patch("/dispatch/issues/{issue_id}")
def dispatch_update_issue(issue_id: UUID, payload: IssueUpdateRequest, request: Request,
                          db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    from app.services.dispatch_admin_service import DispatchAdminService
    issue = DispatchAdminService(db).update_issue(issue_id=issue_id, admin=admin, status=payload.status,
                                                  note=payload.note, ip=_client_ip(request))
    return {"id": str(issue.id), "status": issue.status}


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


# ---- Security: who is doing what, from where -------------------------------------------------
def _activity_row(entry, user):
    return {"id": str(entry.id), "at": entry.created_at, "event": entry.event,
            "user_id": str(entry.user_id) if entry.user_id else None,
            "user_name": user.full_name if user else None, "user_email": user.email if user else None,
            "role": entry.role or (user.role if user else None),
            "method": entry.method, "path": entry.path, "status_code": entry.status_code,
            "ip_address": entry.ip_address, "device_id": entry.device_id, "user_agent": entry.user_agent,
            "details": entry.details or {}}


@router.get("/activity")
def activity_log(
    event: str | None = None, user_id: UUID | None = None, email: str | None = None,
    ip: str | None = None, device_id: str | None = None, before: str | None = None,
    limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN)),
):
    """Newest first. Filter by event, person (id or email), IP or device; page with `before`."""
    from datetime import datetime
    from app.models.activity_log import ActivityLog
    query = db.query(ActivityLog, User).outerjoin(User, User.id == ActivityLog.user_id)
    if event:
        query = query.filter(ActivityLog.event == event)
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    if email:
        needle = email.strip().lower()
        # Failed sign-ins have no user, only the email that was tried.
        query = query.filter((User.email.ilike(f"%{needle}%")) | (ActivityLog.details["email"].astext.ilike(f"%{needle}%")))
    if ip:
        query = query.filter(ActivityLog.ip_address == ip.strip())
    if device_id:
        query = query.filter(ActivityLog.device_id == device_id.strip())
    if before:
        try:
            query = query.filter(ActivityLog.created_at < datetime.fromisoformat(before))
        except ValueError as exc:
            raise HTTPException(422, "before must be an ISO timestamp.") from exc
    rows = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(max(1, min(limit, 200))).all()
    return [_activity_row(entry, user) for entry, user in rows]


@router.get("/activity/summary")
def activity_summary(db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """At-a-glance security picture for the last 24 hours."""
    from datetime import timedelta
    from app.core.config import settings
    from sqlalchemy import func
    from app.models.activity_log import ActivityLog
    now = utcnow()
    day, recent = now - timedelta(hours=24), now - timedelta(minutes=15)
    def count(*conditions):
        return db.query(func.count(ActivityLog.id)).filter(*conditions).scalar() or 0
    failed_by_ip = (db.query(ActivityLog.ip_address, func.count(ActivityLog.id).label("n"))
                    .filter(ActivityLog.created_at >= day,
                            ActivityLog.event.in_(["sign_in_failed", "admin_sign_in_failed"]),
                            ActivityLog.ip_address.is_not(None))
                    .group_by(ActivityLog.ip_address).order_by(func.count(ActivityLog.id).desc()).limit(5).all())
    return {
        "active_now": db.query(func.count(func.distinct(ActivityLog.user_id)))
                        .filter(ActivityLog.created_at >= recent, ActivityLog.user_id.is_not(None)).scalar() or 0,
        "sign_ins_24h": count(ActivityLog.created_at >= day, ActivityLog.event.in_(["sign_in", "admin_sign_in"])),
        "failed_sign_ins_24h": count(ActivityLog.created_at >= day,
                                     ActivityLog.event.in_(["sign_in_failed", "admin_sign_in_failed"])),
        "admin_sign_ins_24h": count(ActivityLog.created_at >= day, ActivityLog.event == "admin_sign_in"),
        "distinct_ips_24h": db.query(func.count(func.distinct(ActivityLog.ip_address)))
                              .filter(ActivityLog.created_at >= day).scalar() or 0,
        "top_failed_ips": [{"ip_address": ip, "attempts": n} for ip, n in failed_by_ip],
        "retention_days": settings.ACTIVITY_LOG_RETENTION_DAYS,
    }


@router.get("/users/{user_id}/footprint")
def user_footprint(user_id: UUID, db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Every IP and device a person has used, with first and last seen, for tracing an account."""
    from sqlalchemy import func
    from app.models.activity_log import ActivityLog
    person = db.get(User, user_id)
    if person is None:
        raise HTTPException(404, "User not found.")
    def grouped(column):
        return [{"value": value, "first_seen": first, "last_seen": last, "events": n}
                for value, first, last, n in db.query(column, func.min(ActivityLog.created_at),
                                                      func.max(ActivityLog.created_at), func.count(ActivityLog.id))
                .filter(ActivityLog.user_id == user_id, column.is_not(None))
                .group_by(column).order_by(func.max(ActivityLog.created_at).desc()).limit(50).all()]
    return {"user": {"id": str(person.id), "name": person.full_name, "email": person.email, "role": person.role,
                     "is_active": person.is_active},
            "ips": grouped(ActivityLog.ip_address), "devices": grouped(ActivityLog.device_id)}


@router.get("/audit-logs")
def audit_logs(limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Admin and system actions (approvals, dispatch changes, ...), newest first."""
    from app.models.audit_log import AuditLog
    rows = (db.query(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_user_id)
            .order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 200))).all())
    return [{"id": str(log.id), "action": log.action, "resource_type": log.resource_type,
             "resource_id": str(log.resource_id) if log.resource_id else None,
             "actor_email": actor.email if actor else None, "ip_address": log.ip_address,
             "created_at": log.created_at} for log, actor in rows]


# ---- Email delivery ---------------------------------------------------------------------------
@router.get("/email/status")
def email_status(db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Is outgoing email configured, and how many people still haven't confirmed their email?"""
    from sqlalchemy import func
    from app.integrations.notifications.email import provider_status
    from app.services.auth_email_outbox_service import AuthEmailOutboxService
    unverified = (db.query(func.count(User.id))
                  .filter(User.is_active.is_(True), User.is_email_verified.is_(False), User.role != "admin").scalar() or 0)
    outbox = AuthEmailOutboxService(db)
    return {**provider_status(), "unverified_accounts": unverified,
            "emails_waiting": outbox.pending_count(), "last_error": outbox.last_error()}


@router.post("/email/verification-backfill", status_code=202)
def email_verification_backfill(request: Request, background: BackgroundTasks,
                                db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.ADMIN))):
    """Email a fresh confirmation link to everyone who registered but never confirmed."""
    from app.integrations.notifications.email import provider_status
    from app.services.auth_email_outbox_service import AuthEmailOutboxService, send_in_background
    status = provider_status()
    if not status["ready"]:
        raise HTTPException(409, f"Email isn't configured yet: {status['problem']}")
    queued = AuthEmailOutboxService(db).queue_for_unverified()
    _audit(db, admin, request, "email.verification_backfill", None)
    db.commit()
    from app.core.config import settings
    if settings.APP_ENV != "test":
        background.add_task(send_in_background, None, None)  # until every queued email is sent
    return {"queued": queued}



@router.get("/routing/health")
def routing_health(admin: User = Depends(require_roles(Role.ADMIN))):
    """Which road-routing provider is in use, is it answering, and is it paused after failures."""
    from app.services.route_service import health
    return health()
