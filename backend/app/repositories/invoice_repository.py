from sqlalchemy.orm import Session
from app.models.invoice import Invoice


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order_id(self, order_id):
        return self.db.query(Invoice).filter(Invoice.order_id == order_id).first()

    def get_by_invoice_number(self, invoice_number: str):
        return self.db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
