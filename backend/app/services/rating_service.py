"""Read-side aggregate rating breakdowns for a professional/vendor."""
from sqlalchemy.orm import Session


class RatingService:
    def __init__(self, db: Session):
        self.db = db

    def get_rating_breakdown(self, professional_user_id) -> dict:
        """Returns e.g. {"average": 4.6, "count": 132, "distribution": {5: 90, 4: 30, ...}}."""
        raise NotImplementedError("Aggregate query over reviews/ratings joined by reviewee_user_id.")
