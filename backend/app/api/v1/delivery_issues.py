"""Authorized courier incident reports; modeled on Sage disruption intake."""
import uuid
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from app.core.database import get_db
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
    issue = DispatchIssueReport(delivery_id=delivery_id, courier_id=user.id, **payload.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
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
