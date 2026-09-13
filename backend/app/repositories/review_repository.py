from sqlalchemy.orm import Session
from app.models.review import Review


class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order_id(self, order_id):
        return self.db.query(Review).filter(Review.order_id == order_id).first()

    def list_for_reviewee(self, reviewee_user_id, *, offset: int = 0, limit: int = 20):
        return (
            self.db.query(Review)
            .filter(Review.reviewee_user_id == reviewee_user_id)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
