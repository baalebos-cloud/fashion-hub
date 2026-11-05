"""
Shareable recipient tracking links.

Owner endpoints (/orders/{id}/share-links) need the buyer's login. The public
endpoint (/public/track/{token}) needs no login but is rate-limited, returns a
deliberately narrow view, and is never cached or indexed.
"""
import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.services.share_link_service import ShareLinkService, share_url

router = APIRouter(tags=["Tracking links"])


class CreateShareLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(None, max_length=60)


@router.post("/orders/{order_id}/share-links", status_code=201)
@limiter.limit("10/hour")
def create_share_link(request: Request, order_id: uuid.UUID, payload: CreateShareLinkRequest,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns the link URL once; only a hash of its token is stored."""
    link, token = ShareLinkService(db).create(order_id=order_id, actor=user, label=payload.label)
    return {"id": str(link.id), "url": share_url(token), "label": link.label, "expires_at": link.expires_at}


@router.get("/orders/{order_id}/share-links")
def list_share_links(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ShareLinkService(db).list_for_owner(order_id=order_id, actor=user)


@router.delete("/orders/{order_id}/share-links/{link_id}", status_code=204)
def revoke_share_link(order_id: uuid.UUID, link_id: uuid.UUID,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ShareLinkService(db).revoke(order_id=order_id, link_id=link_id, actor=user)


@router.get("/public/track/{token}")
@limiter.limit("30/minute")
def public_tracking(request: Request, response: Response, token: str, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"
    return ShareLinkService(db).public_view(token)
