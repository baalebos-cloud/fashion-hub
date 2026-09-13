"""Receipt generation, issued once a payment is confirmed successful."""
from sqlalchemy.orm import Session

from app.utils.invoice_number import generate_receipt_number


class ReceiptService:
    def __init__(self, db: Session):
        self.db = db

    def generate_for_payment(self, payment_id: str, invoice_id: str):
        from app.models.payment import Payment
        from app.models.receipt import Receipt

        payment = self.db.get(Payment, payment_id)
        receipt = Receipt(
            receipt_number=generate_receipt_number(),
            invoice_id=invoice_id,
            payment_id=payment_id,
            amount_paid=payment.amount,
            currency=payment.currency,
        )
        self.db.add(receipt)
        self.db.commit()
        self.db.refresh(receipt)
        return receipt
