from sqlalchemy.orm import Session
from app.models.kyc_verification import KYCVerification
from app.models.kyb_verification import KYBVerification


class KYCRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_kyc_for_user(self, user_id):
        return (
            self.db.query(KYCVerification)
            .filter(KYCVerification.user_id == user_id)
            .order_by(KYCVerification.created_at.desc())
            .first()
        )

    def get_latest_kyb_for_owner(self, business_owner_user_id):
        return (
            self.db.query(KYBVerification)
            .filter(KYBVerification.business_owner_user_id == business_owner_user_id)
            .order_by(KYBVerification.created_at.desc())
            .first()
        )
