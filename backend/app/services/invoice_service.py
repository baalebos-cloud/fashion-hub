"""
Invoice generation and PDF rendering.

Invoices are generated automatically after successful payment (triggered by
payment_service via a background task) and snapshot line items/prices at
that moment, so they remain historically accurate even if catalog prices
change later.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.timezone import utcnow
from app.utils.invoice_number import generate_invoice_number


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def generate_for_order(self, order_id: str):
        from app.models.invoice import Invoice
        from app.models.order import Order
        from app.models.order_item import OrderItem

        order = self.db.get(Order, order_id)
        if not order:
            raise NotFoundError("Order not found.")

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        line_items_snapshot = [
            {
                "name": item.name_snapshot,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
                "line_total": float(item.line_total),
            }
            for item in items
        ]

        invoice = Invoice(
            invoice_number=generate_invoice_number(),
            order_id=order.id,
            issued_to_user_id=order.buyer_user_id,
            issued_by_user_id=order.seller_user_id,
            line_items_snapshot=line_items_snapshot,
            subtotal=order.subtotal,
            delivery_fee=order.delivery_fee,
            tax_amount=order.tax_amount,
            discount_amount=order.discount_amount,
            total_amount=order.total_amount,
            currency=order.currency,
            payment_status="successful",
            order_date=order.ordered_at,
            payment_date=order.paid_at or utcnow(),
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        from app.workers.invoice_tasks import render_invoice_pdf_task
        render_invoice_pdf_task.delay(invoice_id=str(invoice.id))

        return invoice

    def render_pdf(self, invoice_id: str):
        """Renders templates/invoices/invoice.html to PDF and uploads it via
        the storage integration, then emails it to both parties. Requires a
        PDF rendering library (e.g. WeasyPrint) -- wire in via the pdf skill
        conventions used elsewhere in this project."""
        raise NotImplementedError("Wire in PDF rendering (WeasyPrint/wkhtmltopdf) + storage upload here.")
