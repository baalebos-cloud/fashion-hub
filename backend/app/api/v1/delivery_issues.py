"""Authorized courier incident reports; modeled on Sage disruption intake."""
import uuid
import logging

logger = logging.getLogger(__name__)
from typing import Literal
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.integrations.storage.object_storage import get_storage_provider, build_object_key
from app.utils.file_upload import validate_upload, MAX_UPLOAD_SIZE_BYTES
from app.core.exceptions import NotFoundError
from app.core.permissions import Role, require_roles
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_issue import DispatchIssueReport
from app.models.user import User

router = APIRouter(prefix="/deliveries", tags=["Delivery Issues"])
ACTIVE_STATUSES = {"assigned", "picked_up", "in_transit", "out_for_delivery"}

class IssueRequest(BaseModel):
    issue_type: Literal["CUSTOMER_UNREACHABLE", "WRONG_ADDRESS", "PACKAGE_DAMAGED",
                        "TRAFFIC_ACCIDENT_DELAY", "RECIPIENT_REJECTED", "VEHICLE_BREAKDOWN"]
    description: str = Field(min_length=5, max_length=3000)
    photo_evidence_url: str | None = Field(None, max_length=1024)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def valid_location(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both coordinates or neither.")
        return self


def assigned_delivery(delivery_id: uuid.UUID, user: User, db: Session, active_only: bool):
    query = (db.query(Delivery)
             .join(DeliveryPartner, Delivery.delivery_partner_id == DeliveryPartner.id)
             .filter(Delivery.id == delivery_id, DeliveryPartner.user_id == user.id,
                     DeliveryPartner.is_verified.is_(True)))
    if active_only:
        query = query.filter(Delivery.status.in_(ACTIVE_STATUSES))
    delivery = query.first()
    if delivery is None:
        raise NotFoundError("Assigned delivery not found.")
    return delivery


@router.post("/{delivery_id}/issues", status_code=201)
def create_delivery_issue(delivery_id: uuid.UUID, payload: IssueRequest,
                          user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
                          db: Session = Depends(get_db)):
    assigned_delivery(delivery_id, user, db, active_only=True)
    if payload.photo_evidence_url and not payload.photo_evidence_url.startswith(f'delivery-issues/{delivery_id}/'):
        raise HTTPException(status_code=422, detail='Evidence must belong to this delivery.')
    issue = DispatchIssueReport(delivery_id=delivery_id, courier_id=user.id, **payload.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    try:
        from app.workers.delivery_tasks import notify_dispatch_issue_task
        notify_dispatch_issue_task.delay(str(issue.id))
    except Exception as exc:
        # Durable issue reporting must not fail just because notifications are unavailable.
        logger.error("dispatch_issue_notification_queue_failed type=%s issue_id=%s", type(exc).__name__, issue.id)
    return {"id": str(issue.id), "delivery_id": str(issue.delivery_id),
            "issue_type": issue.issue_type, "status": issue.status,
            "created_at": issue.created_at}


@router.get("/{delivery_id}/issues")
def list_delivery_issues(delivery_id: uuid.UUID,
                         user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
                         db: Session = Depends(get_db)):
    assigned_delivery(delivery_id, user, db, active_only=False)
    reports = (db.query(DispatchIssueReport)
               .filter(DispatchIssueReport.delivery_id == delivery_id)
               .order_by(DispatchIssueReport.created_at.desc()).limit(100).all())
    return [{"id": str(x.id), "issue_type": x.issue_type, "description": x.description,
             "status": x.status, "created_at": x.created_at} for x in reports]


@router.post("/{delivery_id}/issue-evidence", status_code=201)
async def upload_issue_evidence(delivery_id: uuid.UUID, file: UploadFile = File(...),
                                user: User = Depends(require_roles(Role.DELIVERY_PARTNER)),
                                db: Session = Depends(get_db)):
    assigned_delivery(delivery_id, user, db, active_only=True)
    if settings.APP_ENV in {"staging", "production"} and settings.STORAGE_PROVIDER == "local":
        raise HTTPException(503, detail="Persistent private storage is required.")
    mime = (file.content_type or "").lower()
    data = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    await file.close()
    validate_upload(content_type=mime, size_bytes=len(data))
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[mime]
    valid = (mime == "image/jpeg" and data.startswith(bytes((255, 216, 255)))) or (
        mime == "image/png" and data.startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10)))) or (
        mime == "image/webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    if not valid:
        raise HTTPException(422, detail="Image content does not match file type.")
    key = build_object_key(folder=f"delivery-issues/{delivery_id}", filename=f"evidence.{ext}")
    key = get_storage_provider().upload(key=key, file_bytes=data, content_type=mime, is_public=False)
    return {"document_storage_key": key, "status": "uploaded"}
