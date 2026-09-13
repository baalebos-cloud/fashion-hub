"""
Review creation, restricted to orders whose status is RECEIVED/COMPLETED.
This is the authoritative enforcement point referenced by the
POST /orders/{order_id}/review route stub.
"""
from sqlalchemy.orm import Session

from app.core.constants import CustomerOrderStatus
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_review(self, *, order, reviewer, comment: str | None, score: int):
        from app.models.rating import Rating
        from app.models.review import Review

        if str(order.buyer_user_id) != str(reviewer.id):
            raise ForbiddenError("Only the customer who placed this order can review it.")
        if order.status not in (CustomerOrderStatus.RECEIVED.value, CustomerOrderStatus.COMPLETED.value):
            raise ConflictError("You can only review an order after it has been received.")

        existing = self.db.query(Review).filter(Review.order_id == order.id).first()
        if existing:
            raise ConflictError("This order has already been reviewed.")

        review = Review(
            order_id=order.id,
            reviewer_user_id=reviewer.id,
            reviewee_user_id=order.seller_user_id,
            comment=comment,
        )
        self.db.add(review)
        self.db.flush()
        self.db.add(Rating(review_id=review.id, axis="overall", score=score))
        self.db.commit()
        self.db.refresh(review)

        self._recalculate_average_rating(order.seller_user_id)
        return review

    def _recalculate_average_rating(self, professional_user_id):
        """Recompute Professional.average_rating/review_count. Left as a
        TODO for the full implementation -- requires joining
        reviews -> ratings -> professionals by user_id."""
        pass
