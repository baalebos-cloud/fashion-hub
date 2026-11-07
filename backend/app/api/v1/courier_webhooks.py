"""Status updates from external courier companies. Signed; duplicates are ignored."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.integrations.couriers import get_courier

router = APIRouter(prefix="/webhooks/couriers", tags=["Courier webhooks"])


@router.post("/{courier_name}", include_in_schema=False)
@limiter.limit("300/minute")
async def courier_webhook(courier_name: str, request: Request, db: Session = Depends(get_db)):
    courier = get_courier(courier_name)
    if courier is None:
        raise HTTPException(404, "Unknown courier.")
    body = await request.body()
    if len(body) > 64_000 or not courier.verify_webhook(body, {k.lower(): v for k, v in request.headers.items()}):
        raise HTTPException(401, "Invalid signature.")
    try:
        event = courier.parse_webhook(body)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, "Unreadable courier event.") from exc
    from app.services.external_courier_service import ExternalCourierService
    outcome = ExternalCourierService(db).handle_event(courier_name, event)
    # 200 for duplicates and unknown shipments too, so the courier stops retrying.
    return {"received": True, "outcome": outcome}
