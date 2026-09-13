import uuid
from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    cart_id: uuid.UUID
    delivery_address_id: uuid.UUID
