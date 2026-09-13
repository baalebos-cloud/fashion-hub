"""
Importing every model module here ensures Base.metadata is fully populated
before Alembic's autogenerate (env.py) or Base.metadata.create_all() runs.
Add new models to this list as they're created.
"""
from app.models.user import User, RefreshSession
from app.models.customer import Customer
from app.models.professional import Professional
from app.models.tailor import Tailor
from app.models.designer import Designer
from app.models.vendor import Vendor
from app.models.vendor_category import VendorCategory
from app.models.vendor_product import VendorProduct
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status import OrderStatusDefinition
from app.models.order_timeline import OrderTimelineEntry
from app.models.payment import Payment
from app.models.payment_transaction import PaymentTransaction
from app.models.refund import Refund
from app.models.invoice import Invoice
from app.models.receipt import Receipt
from app.models.payment_consent import PaymentConsent
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.delivery import Delivery
from app.models.delivery_tracking import DeliveryTracking
from app.models.tracking_event import TrackingEvent
from app.models.location import Location
from app.models.address import Address
from app.models.measurement import Measurement
from app.models.measurement_profile import MeasurementProfile
from app.models.category import Category
from app.models.design import Design
from app.models.design_image import DesignImage
from app.models.review import Review
from app.models.rating import Rating
from app.models.notification import Notification
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage
from app.models.ai_action import AIAction
from app.models.kyc_verification import KYCVerification
from app.models.kyb_verification import KYBVerification
from app.models.verification_document import VerificationDocument
from app.models.favorite import Favorite
from app.models.audit_log import AuditLog

__all__ = [
    "User", "RefreshSession", "Customer", "Professional", "Tailor", "Designer",
    "Vendor", "VendorCategory", "VendorProduct", "ProductVariant", "Inventory",
    "Cart", "CartItem", "Order", "OrderItem", "OrderStatusDefinition", "OrderTimelineEntry",
    "Payment", "PaymentTransaction", "Refund", "Invoice", "Receipt", "PaymentConsent",
    "DeliveryPartner", "DeliveryRequest", "Delivery", "DeliveryTracking", "TrackingEvent",
    "Location", "Address", "Measurement", "MeasurementProfile", "Category", "Design",
    "DesignImage", "Review", "Rating", "Notification", "Conversation", "Message",
    "AIConversation", "AIMessage", "AIAction", "KYCVerification", "KYBVerification",
    "VerificationDocument", "Favorite", "AuditLog",
]
