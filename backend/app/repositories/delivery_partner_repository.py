from sqlalchemy.orm import Session
from app.models.delivery_partner import DeliveryPartner


class DeliveryPartnerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id):
        return self.db.query(DeliveryPartner).filter(DeliveryPartner.user_id == user_id).first()

    def list_available(self, *, offset: int = 0, limit: int = 20):
        return (
            self.db.query(DeliveryPartner)
            .filter(DeliveryPartner.is_available.is_(True), DeliveryPartner.is_verified.is_(True))
            .offset(offset)
            .limit(limit)
            .all()
        )
