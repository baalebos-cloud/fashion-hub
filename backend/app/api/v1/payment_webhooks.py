"""
/api/v1/payments/webhooks

Webhook endpoints read the RAW request body (not parsed JSON) because
signature verification must run over the exact bytes the provider signed.
No authentication middleware runs here -- trust is established purely via
the provider's cryptographic signature (see PaymentProvider.verify_webhook_signature).
"""
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments/webhooks", tags=["Payment Webhooks"])


@router.post("/paystack", status_code=200)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    body_json = await request.json()

    service = PaymentService(db)
    service.process_webhook(
        payload=raw_body,
        signature_header=x_paystack_signature,
        provider_event_id=body_json.get("id") or body_json["data"]["reference"],
        event_type=body_json.get("event", "unknown"),
        provider_reference=body_json["data"]["reference"],
        amount=body_json["data"]["amount"] / 100,
    )
    # Always return 200 quickly once the event is durably recorded, so the
    # provider doesn't endlessly retry (which is a normal, expected source
    # of duplicate deliveries we already handle idempotently).
    return {"received": True}


@router.post("/flutterwave", status_code=200)
async def flutterwave_webhook(
    request: Request,
    verif_hash: str = Header(default="", alias="verif-hash"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    body_json = await request.json()
    data = body_json.get("data", {})

    service = PaymentService(db)
    service.process_webhook(
        payload=raw_body,
        signature_header=verif_hash,
        provider_event_id=str(data.get("id")),
        event_type=body_json.get("event", "unknown"),
        provider_reference=data.get("tx_ref", ""),
        amount=data.get("amount", 0),
    )
    return {"received": True}
