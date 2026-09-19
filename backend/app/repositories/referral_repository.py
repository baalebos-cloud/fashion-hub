from typing import Optional
from sqlalchemy.orm import Session
from app.models.referral import Referral


class ReferralRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_referred_user(self, referred_user_id) -> Optional[Referral]:
        return self.db.query(Referral).filter(Referral.referred_user_id == referred_user_id).first()

    def list_for_referrer(self, referrer_user_id, *, offset: int = 0, limit: int = 20) -> list[Referral]:
        return (
            self.db.query(Referral)
            .filter(Referral.referrer_user_id == referrer_user_id)
            .order_by(Referral.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def add(self, referral: Referral) -> Referral:
        self.db.add(referral)
        return referral
