"""Opt-in Interswitch sandbox checkout, authoritative verification and redirect."""
import re
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.payment_outbox import PaymentOutbox
from app.models.user import User
from app.schemas.payment import PaymentResponse
from app.services.interswitch_sandbox_service import InterswitchSandboxService

router = APIRouter(prefix="/interswitch", tags=["Interswitch sandbox"])


class InterswitchCheckoutRequest(BaseModel):
    order_id: uuid.UUID


class InterswitchCheckoutResponse(BaseModel):
    action_url: str
    fields: dict[str, str]


@router.post("/checkout", response_model=InterswitchCheckoutResponse)
def initialize_checkout(payload: InterswitchCheckoutRequest,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    result = InterswitchSandboxService(db).initialize_checkout(
        order_id=payload.order_id, buyer_user_id=current_user.id,
        customer_email=current_user.email,
    )
    return InterswitchCheckoutResponse(action_url=result.action_url, fields=result.fields)


@router.get("/{provider_reference}/verify", response_model=PaymentResponse)
def verify_checkout(provider_reference: str,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    payment = InterswitchSandboxService(db).verify_and_confirm(
        provider_reference, buyer_user_id=current_user.id,
    )
    result = PaymentResponse.model_validate(payment)
    result.requires_review = db.query(PaymentOutbox.id).filter_by(
        payment_id=payment.id, kind="payment.review",
    ).first() is not None
    return result


@router.post("/return")
def browser_return(txnref: str = Form(default="")):
    # This POST is an untrusted browser notification, NEVER a settlement event.
    # Send the buyer to an authenticated page that independently requeries.
    params = {"provider": "interswitch"}
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", txnref):
        params["reference"] = txnref
    destination = f"{settings.FRONTEND_URL.rstrip('/')}/app/customer/payment/success"
    return RedirectResponse(url=f"{destination}?{urlencode(params)}", status_code=303)
