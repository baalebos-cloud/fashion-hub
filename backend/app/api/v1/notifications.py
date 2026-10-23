"""Authenticated in-app notification feed and owner-only read acknowledgement."""
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user
from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationPage(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=NotificationPage)
def list_notifications(
    pagination: PaginationParams = Depends(),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Never expose internal email outbox records or their encrypted tokens
    # through this user-facing feed.
    query = db.query(Notification).filter(
        Notification.recipient_user_id == current_user.id,
        Notification.channel == "in_app",
    )
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    total = query.count()
    items = (query.order_by(Notification.created_at.desc(), Notification.id.desc())
             .offset(pagination.offset).limit(pagination.page_size).all())
    return {"items": items, "total": total, "page": pagination.page,
            "page_size": pagination.page_size}


@router.post("/{notification_id}/read", status_code=204)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_user_id == current_user.id,
        Notification.channel == "in_app",
    ).with_for_update().first())
    if not notification:
        # No information about another user's notifications is disclosed.
        raise NotFoundError("Notification not found.")
    if not notification.is_read:
        notification.is_read = True
        db.commit()
    return None
