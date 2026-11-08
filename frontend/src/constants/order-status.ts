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

/** What happens next, in the customer's words, for each live status. */
export const CUSTOMER_ORDER_NEXT_STEP: Partial<Record<CustomerOrderStatus, string>> = {
  pending: "Complete payment to send it to the tailor",
  paid: "Waiting for the tailor to accept",
  accepted: "Accepted · production starts soon",
  in_production: "Being made",
  ready_for_delivery: "Ready · waiting for a rider",
  shipped: "On its way to you",
  out_for_delivery: "On its way to you · track it",
  delivered: "Delivered · confirm you received it",
};

/** What the tailor/designer should do next, for each status of an order they're making. */
export const PROFESSIONAL_ORDER_NEXT_STEP: Partial<Record<CustomerOrderStatus, string>> = {
  pending: "Waiting for the customer to pay",
  paid: "Accept or decline this order",
  accepted: "Start production",
  in_production: "Mark ready when it's finished",
  ready_for_delivery: "Request a rider",
  shipped: "Waiting for a rider",
  out_for_delivery: "With the rider",
  delivered: "Waiting for the customer to confirm",
};

/** Board columns for the workroom, built only from the platform's real statuses. */
export const WORKROOM_STAGES: { key: string; title: string; statuses: CustomerOrderStatus[] }[] = [
  { key: "new", title: "New", statuses: ["pending", "paid"] },
  { key: "accepted", title: "Accepted", statuses: ["accepted"] },
  { key: "making", title: "Being made", statuses: ["in_production"] },
  { key: "ready", title: "Ready to send", statuses: ["ready_for_delivery", "shipped"] },
  { key: "delivery", title: "With the rider", statuses: ["out_for_delivery", "delivered"] },
  { key: "done", title: "Done", statuses: ["received", "completed"] },
];
