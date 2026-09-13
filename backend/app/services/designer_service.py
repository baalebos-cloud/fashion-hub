"""Designer-specific profile operations (style tags, signature collections)."""
from sqlalchemy.orm import Session


class DesignerService:
    def __init__(self, db: Session):
        self.db = db
