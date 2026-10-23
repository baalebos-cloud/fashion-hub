"""Persist buyer reviews and recalculate professional/vendor rating aggregates."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.order import Order
from app.models.professional import Professional
from app.models.rating import Rating
from app.models.review import Review
from app.models.vendor import Vendor


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_review(self, *, order, reviewer, comment: str | None, score: int):
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValidationAppError("Rating must be between 1 and 5.")
        order = (self.db.query(Order).filter(Order.id == order.id)
                 .with_for_update().populate_existing().first())
        if not order:
            raise NotFoundError("Order not found.")
        if str(order.buyer_user_id) != str(reviewer.id):
            raise ForbiddenError("Only the buyer of this order can review it.")
        if order.status not in {"received", "completed"}:
            raise ConflictError("You can only review an order after it has been received.")
        if self.db.query(Review).filter_by(order_id=order.id).first():
            raise ConflictError("This order has already been reviewed.")

        review = Review(order_id=order.id, reviewer_user_id=reviewer.id,
                        reviewee_user_id=order.seller_user_id, comment=comment)
        self.db.add(review)
        self.db.flush()
        self.db.add(Rating(review_id=review.id, axis="overall", score=score))
        self.db.flush()
        self._recalculate_average_rating(order.seller_user_id)
        self.db.commit()
        self.db.refresh(review)
        return review

    def _recalculate_average_rating(self, seller_user_id):
        average, count = (self.db.query(func.avg(Rating.score), func.count(Rating.id))
                          .join(Review, Review.id == Rating.review_id)
                          .filter(Review.reviewee_user_id == seller_user_id, Rating.axis == "overall")
                          .one())
        professional = self.db.query(Professional).filter_by(user_id=seller_user_id).first()
        if professional:
            professional.average_rating = round(float(average or 0), 2)
            professional.review_count = count
        vendor = self.db.query(Vendor).filter_by(user_id=seller_user_id).first()
        if vendor:
            vendor.average_rating = round(float(average or 0), 2)

    def list_reviews(self, *, reviewee_user_id=None, reviewer_user_id=None):
        query = (self.db.query(Review, Rating.score)
                 .join(Rating, (Rating.review_id == Review.id) & (Rating.axis == "overall")))
        if reviewee_user_id is not None:
            query = query.filter(Review.reviewee_user_id == reviewee_user_id)
        if reviewer_user_id is not None:
            query = query.filter(Review.reviewer_user_id == reviewer_user_id)
        rows = query.order_by(Review.created_at.desc(), Review.id.desc()).limit(100).all()
        return [{"id": row.id, "order_id": row.order_id, "comment": row.comment,
                 "score": score, "created_at": row.created_at} for row, score in rows]
