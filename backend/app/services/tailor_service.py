"""Tailor-specific profile operations (garment specialties, turnaround time)."""
from sqlalchemy.orm import Session


class TailorService:
    def __init__(self, db: Session):
        self.db = db
