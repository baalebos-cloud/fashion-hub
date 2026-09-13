from sqlalchemy.orm import Session
from app.models.cart import Cart
from app.models.cart_item import CartItem


class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_for_owner(self, owner_user_id):
        return self.db.query(Cart).filter(Cart.owner_user_id == owner_user_id, Cart.status == "active").first()

    def list_items(self, cart_id):
        return self.db.query(CartItem).filter(CartItem.cart_id == cart_id).all()
