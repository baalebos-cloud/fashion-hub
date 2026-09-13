from sqlalchemy.orm import Session
from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id):
        return self.db.query(Customer).filter(Customer.user_id == user_id).first()
