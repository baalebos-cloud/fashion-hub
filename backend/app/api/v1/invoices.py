"""Invoice snapshots are visible only to the order parties and admins."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.user import User
from app.schemas.invoice import InvoiceResponse

router = APIRouter(prefix='/invoices', tags=['Invoices'])


def assert_access(order, user):
    if not order:
        raise NotFoundError('Order not found.')
    if user.role != 'admin' and user.id not in {order.buyer_user_id, order.seller_user_id}:
        raise ForbiddenError('You do not have permission to view this invoice.')


@router.get('/by-order/{order_id}', response_model=InvoiceResponse)
def by_order(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assert_access(db.get(Order, order_id), user)
    invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if not invoice:
        raise NotFoundError('Invoice is not ready yet. Please try again shortly.')
    return invoice


@router.get('/{invoice_id}', response_model=InvoiceResponse)
def by_id(invoice_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise NotFoundError('Invoice not found.')
    assert_access(db.get(Order, invoice.order_id), user)
    return invoice
