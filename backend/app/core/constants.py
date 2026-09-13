"""
Application-wide constants and enums shared across models/schemas/services.

Keeping order/payment/delivery state machines defined ONCE here (rather than
scattered as magic strings) is what makes `order_service.transition()` able
to enforce valid transitions centrally.
"""
from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    TAILOR = "tailor"
    DESIGNER = "designer"
    VENDOR = "vendor"
    DELIVERY_PARTNER = "delivery_partner"
    ADMIN = "admin"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CustomerOrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    ACCEPTED = "accepted"
    IN_PRODUCTION = "in_production"
    READY_FOR_DELIVERY = "ready_for_delivery"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    RECEIVED = "received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    REFUNDED = "refunded"


# Ordered, valid forward transitions for a customer order. Any transition not
# listed here (e.g. PENDING -> RECEIVED) must be rejected by order_service.
CUSTOMER_ORDER_TRANSITIONS: dict[CustomerOrderStatus, list[CustomerOrderStatus]] = {
    CustomerOrderStatus.PENDING: [CustomerOrderStatus.PAID, CustomerOrderStatus.CANCELLED],
    CustomerOrderStatus.PAID: [CustomerOrderStatus.ACCEPTED, CustomerOrderStatus.REJECTED, CustomerOrderStatus.REFUNDED],
    CustomerOrderStatus.ACCEPTED: [CustomerOrderStatus.IN_PRODUCTION, CustomerOrderStatus.CANCELLED],
    CustomerOrderStatus.IN_PRODUCTION: [CustomerOrderStatus.READY_FOR_DELIVERY],
    CustomerOrderStatus.READY_FOR_DELIVERY: [CustomerOrderStatus.SHIPPED],
    CustomerOrderStatus.SHIPPED: [CustomerOrderStatus.OUT_FOR_DELIVERY],
    CustomerOrderStatus.OUT_FOR_DELIVERY: [CustomerOrderStatus.DELIVERED],
    # NOTE: only the customer role may perform DELIVERED -> RECEIVED (enforced
    # in the service layer, not just here).
    CustomerOrderStatus.DELIVERED: [CustomerOrderStatus.RECEIVED],
    CustomerOrderStatus.RECEIVED: [CustomerOrderStatus.COMPLETED],
    CustomerOrderStatus.COMPLETED: [],
    CustomerOrderStatus.CANCELLED: [],
    CustomerOrderStatus.REJECTED: [],
    CustomerOrderStatus.REFUNDED: [],
}


class VendorOrderStatus(str, Enum):
    CART = "cart"
    CHECKOUT = "checkout"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RECEIVED = "received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


VENDOR_ORDER_TRANSITIONS: dict[VendorOrderStatus, list[VendorOrderStatus]] = {
    VendorOrderStatus.CART: [VendorOrderStatus.CHECKOUT],
    VendorOrderStatus.CHECKOUT: [VendorOrderStatus.PAYMENT_PENDING, VendorOrderStatus.CANCELLED],
    VendorOrderStatus.PAYMENT_PENDING: [VendorOrderStatus.PAID, VendorOrderStatus.CANCELLED],
    VendorOrderStatus.PAID: [VendorOrderStatus.CONFIRMED, VendorOrderStatus.REFUNDED],
    VendorOrderStatus.CONFIRMED: [VendorOrderStatus.PROCESSING, VendorOrderStatus.CANCELLED],
    VendorOrderStatus.PROCESSING: [VendorOrderStatus.READY_FOR_PICKUP],
    VendorOrderStatus.READY_FOR_PICKUP: [VendorOrderStatus.PICKED_UP],
    VendorOrderStatus.PICKED_UP: [VendorOrderStatus.IN_TRANSIT],
    VendorOrderStatus.IN_TRANSIT: [VendorOrderStatus.DELIVERED],
    # Only the tailor/designer (the buyer) may perform DELIVERED -> RECEIVED.
    VendorOrderStatus.DELIVERED: [VendorOrderStatus.RECEIVED],
    VendorOrderStatus.RECEIVED: [VendorOrderStatus.COMPLETED],
    VendorOrderStatus.COMPLETED: [],
    VendorOrderStatus.CANCELLED: [],
    VendorOrderStatus.REFUNDED: [],
}


class PaymentStatus(str, Enum):
    INITIALIZED = "initialized"
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REVERSED = "reversed"


class RefundStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    REJECTED = "rejected"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LocationType(str, Enum):
    CUSTOMER_ADDRESS = "customer_address"
    TAILOR_SHOP = "tailor_shop"
    VENDOR_WAREHOUSE = "vendor_warehouse"
    DELIVERY_DROPOFF = "delivery_dropoff"
    DELIVERY_PICKUP = "delivery_pickup"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class ConsentType(str, Enum):
    ORDER_PAYMENT = "order_payment"
    TERMS_OF_SERVICE = "terms_of_service"
    DATA_PROCESSING = "data_processing"
