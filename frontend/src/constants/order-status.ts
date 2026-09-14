import type { CustomerOrderStatus, VendorOrderStatus } from "@/types/order";

/** Display labels + badge tone. Mirrors backend/app/core/constants.py
 * enums exactly — if the backend adds a status, add it here too. */
export const CUSTOMER_ORDER_STATUS_LABELS: Record<CustomerOrderStatus, string> = {
  pending: "Pending",
  paid: "Paid",
  accepted: "Accepted",
  in_production: "In Production",
  ready_for_delivery: "Ready for Delivery",
  shipped: "Shipped",
  out_for_delivery: "Out for Delivery",
  delivered: "Delivered",
  received: "Received",
  completed: "Completed",
  cancelled: "Cancelled",
  rejected: "Rejected",
  refunded: "Refunded",
};

export const VENDOR_ORDER_STATUS_LABELS: Record<VendorOrderStatus, string> = {
  cart: "Cart",
  checkout: "Checkout",
  payment_pending: "Payment Pending",
  paid: "Paid",
  confirmed: "Confirmed",
  processing: "Processing",
  ready_for_pickup: "Ready for Pickup",
  picked_up: "Picked Up",
  in_transit: "In Transit",
  delivered: "Delivered",
  received: "Received",
  completed: "Completed",
  cancelled: "Cancelled",
  refunded: "Refunded",
};

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

export const CUSTOMER_ORDER_STATUS_TONE: Record<CustomerOrderStatus, StatusTone> = {
  pending: "neutral",
  paid: "info",
  accepted: "info",
  in_production: "info",
  ready_for_delivery: "info",
  shipped: "info",
  out_for_delivery: "info",
  delivered: "success",
  received: "success",
  completed: "success",
  cancelled: "danger",
  rejected: "danger",
  refunded: "warning",
};
