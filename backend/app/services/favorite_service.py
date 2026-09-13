"""Favorites (saved professionals/designs/vendor products)."""
from sqlalchemy.orm import Session


class FavoriteService:
    def __init__(self, db: Session):
        self.db = db

    def toggle_favorite(self, *, user_id, favorite_type: str, favorite_ref_id) -> bool:
        """Returns True if now favorited, False if it was removed."""
        from app.models.favorite import Favorite

        existing = (
            self.db.query(Favorite)
            .filter(Favorite.user_id == user_id, Favorite.favorite_type == favorite_type, Favorite.favorite_ref_id == favorite_ref_id)
            .first()
        )
        if existing:
            self.db.delete(existing)
            self.db.commit()
            return False

        self.db.add(Favorite(user_id=user_id, favorite_type=favorite_type, favorite_ref_id=favorite_ref_id))
        self.db.commit()
        return True
