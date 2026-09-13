from sqlalchemy.orm import Session
from app.models.payment_consent import PaymentConsent


class ConsentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **fields) -> PaymentConsent:
        consent = PaymentConsent(**fields)
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        return consent
