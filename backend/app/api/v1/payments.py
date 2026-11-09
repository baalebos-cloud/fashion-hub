"""
/payments

Payment initialization/verification live behind PaymentService (see
backend/docs/payments.md for the full "never trust the client" flow this
implements); this module also exposes the seller-facing payout view.

CRITICAL: /payments/payouts is intentionally restricted to
professional/vendor/admin roles. A customer calling this endpoint gets a
403, never an empty list -- the distinction matters, because an empty
list would look like "no commission," while a 403 correctly signals "this
isn't for you." Never relax this to `get_current_user` alone.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import get_current_user, PaginationParams
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.payment import InitializePaymentRequest, InitializePaymentResponse, PaymentResponse
from app.services.payment_service import PaymentService
from app.services.payout_service import PayoutService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=InitializePaymentResponse)
def initialize_payment(
    payload: InitializePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)
    result = service.initialize_payment_for_order(
        order_id=payload.order_id, customer_email=current_user.email, callback_url=payload.callback_url,
        buyer_user_id=current_user.id,
    )
    return InitializePaymentResponse(**result)


@router.get("/{provider_reference}/verify", response_model=PaymentResponse)
def verify_payment(provider_reference: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = PaymentService(db)
    payment = service.verify_and_confirm(provider_reference, buyer_user_id=current_user.id)
    from app.models.payment_outbox import PaymentOutbox
    result = PaymentResponse.model_validate(payment)
    result.requires_review = db.query(PaymentOutbox.id).filter_by(payment_id=payment.id, kind='payment.review').first() is not None
    return result


@router.get("/payouts", response_model=list[dict])
def list_my_payouts(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Seller-facing earnings view -- shows gross, the platform's commission,
    and net payout per order. This is the ONLY place in the API that ever
    returns commission_rate/commission_amount; no customer-facing endpoint
    (orders, invoices, receipts) includes these fields, by construction --
    see backend/docs/commission.md.
    """
    payouts = PayoutService(db).list_for_seller(current_user.id, offset=pagination.offset, limit=pagination.page_size)
    return [
        {
            "order_id": str(p.order_id),
            "gross_amount": float(p.gross_amount),
            "commission_rate": float(p.commission_rate),
            "commission_amount": float(p.commission_amount),
            "net_amount": float(p.net_amount),
            "currency": p.currency,
            "status": p.status,
            "hold_reason": p.hold_reason,
            "paid_at": p.released_at,
            "created_at": p.created_at,
        }
        for p in payouts
    ]


# ---- Payout bank account (sellers) -------------------------------------------------------------


class PayoutAccountRequest(BaseModel):
    bank_code: str = Field(min_length=2, max_length=16)
    account_number: str = Field(min_length=10, max_length=14)
    password: str = Field(min_length=1, max_length=256)


@router.get("/payout-account/banks")
def payout_banks(current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR))):
    from app.services.seller_bank_account_service import SellerBankAccountService
    return SellerBankAccountService.banks()


@router.get("/payout-account")
def get_payout_account(current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
                       db: Session = Depends(get_db)):
    from app.services.payout_release_service import payouts_on
    from app.services.seller_bank_account_service import SellerBankAccountService
    service = SellerBankAccountService(db)
    return {"account": service.describe(service.get(current_user)), "payouts_enabled": payouts_on()}


@router.put("/payout-account")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def set_payout_account(payload: PayoutAccountRequest, request: Request,
                       current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
                       db: Session = Depends(get_db)):
    """Needs the seller's password: a stolen session must not be able to redirect payouts."""
    from app.services.seller_bank_account_service import SellerBankAccountService
    service = SellerBankAccountService(db)
    return service.describe(service.set(current_user, bank_code=payload.bank_code,
                                        account_number=payload.account_number, password=payload.password))
