"""Opt-in Interswitch sandbox checkout, authoritative verification and redirect."""
import uuid

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
from app.services.interswitch_live_service import InterswitchLiveService
from app.services.interswitch_return import redirect_for_interswitch_return

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
def browser_return(txnref: str = Form(default=""), txn_ref: str = Form(default=""),
                   transactionreference: str = Form(default=""),
                   reference: str = Form(default="")):
    # Navigation only. The authenticated buyer must verify via server requery.
    return RedirectResponse(
        url=redirect_for_interswitch_return(
            txnref=txnref, txn_ref=txn_ref,
            transactionreference=transactionreference, reference=reference,
        ),
        status_code=303,
    )


@router.get("/return")
def browser_return_get(txnref: str = "", txn_ref: str = "",
                       transactionreference: str = "", reference: str = ""):
    return RedirectResponse(
        url=redirect_for_interswitch_return(
            txnref=txnref, txn_ref=txn_ref,
            transactionreference=transactionreference, reference=reference,
        ),
        status_code=303,
    )

@router.post("/live/checkout", response_model=InterswitchCheckoutResponse)
def initialize_live_checkout(payload: InterswitchCheckoutRequest,
                             current_user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Explicit live hosted checkout, disabled unless separately approved."""
    result = InterswitchLiveService(db).initialize_checkout(
        order_id=payload.order_id, buyer_user_id=current_user.id,
        customer_email=current_user.email,
    )
    return InterswitchCheckoutResponse(action_url=result.action_url, fields=result.fields)


@router.get("/live/{provider_reference}/verify", response_model=PaymentResponse)
def verify_live_checkout(provider_reference: str,
                         current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    payment = InterswitchLiveService(db).verify_and_confirm(
        provider_reference, buyer_user_id=current_user.id,
    )
    result = PaymentResponse.model_validate(payment)
    result.requires_review = db.query(PaymentOutbox.id).filter_by(
        payment_id=payment.id, kind="payment.review",
    ).first() is not None
    return result
