from sqlalchemy.orm import Session
from app.models.measurement_profile import MeasurementProfile


class MeasurementRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_customer(self, customer_id):
        return self.db.query(MeasurementProfile).filter(MeasurementProfile.customer_id == customer_id).all()
