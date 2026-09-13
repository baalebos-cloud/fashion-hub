"""Customer-specific profile operations."""
from sqlalchemy.orm import Session


class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id):
        from app.models.customer import Customer

        customer = self.db.query(Customer).filter(Customer.user_id == user_id).first()
        if not customer:
            customer = Customer(user_id=user_id)
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
        return customer
