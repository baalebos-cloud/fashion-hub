"""Validate signatures and bounded payloads before processing provider events."""
import json
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import get_db
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments/webhooks", tags=["Payment Webhooks"])
MAX_WEBHOOK_BYTES = 256 * 1024


async def _receive(request: Request, signature: str, provider: str, db: Session):
    if settings.PAYMENT_PROVIDER != provider:
        raise HTTPException(404, "Payment provider is not enabled.")
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > MAX_WEBHOOK_BYTES:
            raise HTTPException(413, "Webhook payload is too large.")
    raw = bytes(chunks)
    service = PaymentService(db)
    if not service.provider.verify_webhook_signature(payload=raw, signature_header=signature):
        raise HTTPException(401, "Invalid webhook signature.")
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError
        event = body.get("event", "unknown")
        if provider == "paystack" and event in {"refund.pending", "refund.processing",
                                                  "refund.needs-attention", "refund.failed",
                                                  "refund.processed"}:
            if not isinstance(body.get("data"), dict):
                raise ValueError
            from app.services.refund_service import RefundService
            matched = await run_in_threadpool(RefundService(db).record_paystack_event,
                                             event_type=event, payload=body["data"])
            return {"received": True, "reconciled": bool(matched)}
        if event not in {"charge.success", "charge.failed", "payment.successful", "payment.failed"}:
            return {"received": True, "ignored": True}
        data = body["data"]
        reference = data["reference" if provider == "paystack" else "tx_ref"]
        if not isinstance(reference, str) or not reference or len(reference) > 128:
            raise ValueError
        amount = Decimal(str(data["amount"]))
        if not amount.is_finite() or amount < 0:
            raise ValueError
        if provider == "paystack":
            amount /= 100
        # Namespaced IDs prevent collisions between event types/providers.
        event_id = f"{provider}:{event}:{data.get('id', reference)}"
        if len(event_id) > 128:
            raise ValueError
    except (ValueError, KeyError, TypeError, InvalidOperation):
        raise HTTPException(400, "Malformed payment webhook.") from None
    await run_in_threadpool(service.process_webhook,
        payload=raw, signature_header=signature, provider_event_id=event_id,
        event_type=event, provider_reference=reference, amount=amount,
    )
    return {"received": True}


@router.post("/paystack")
async def paystack_webhook(request: Request, x_paystack_signature: str = Header(default=""),
                           db: Session = Depends(get_db)):
    return await _receive(request, x_paystack_signature, "paystack", db)


@router.post("/flutterwave")
async def flutterwave_webhook(request: Request, verif_hash: str = Header(default="", alias="verif-hash"),
                              db: Session = Depends(get_db)):
    return await _receive(request, verif_hash, "flutterwave", db)
