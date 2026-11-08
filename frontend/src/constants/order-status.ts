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
  payment_pending: "Payment pending",
  paid: "Paid",
  confirmed: "Confirmed",
  processing: "Processing",
  ready_for_pickup: "Ready for pickup",
  picked_up: "Picked up",
  in_transit: "In transit",
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

export const VENDOR_ORDER_STATUS_TONE: Partial<Record<VendorOrderStatus, StatusTone>> = {
  payment_pending: "neutral",
  paid: "warning",
  confirmed: "info",
  processing: "info",
  ready_for_pickup: "info",
  picked_up: "info",
  in_transit: "info",
  delivered: "success",
  received: "success",
  completed: "success",
  cancelled: "danger",
  refunded: "neutral",
};

/** What the vendor does next, in plain words. Statuses with no entry need nothing from them. */
export const VENDOR_ORDER_NEXT_STEP: Partial<Record<VendorOrderStatus, string>> = {
  paid: "Confirm you have it",
  confirmed: "Start preparing",
  processing: "Mark ready for pickup",
  ready_for_pickup: "Request a rider",
  picked_up: "With the rider",
  in_transit: "With the rider",
  delivered: "Waiting for the buyer to confirm",
};

/** The vendor's fulfilment steps, matching the backend's vendor order statuses. */
export const VENDOR_FULFILMENT_STEPS: { key: string; title: string; statuses: VendorOrderStatus[] }[] = [
  { key: "received", title: "Order received", statuses: ["paid"] },
  { key: "confirm", title: "Confirmed", statuses: ["confirmed"] },
  { key: "prepare", title: "Preparing", statuses: ["processing"] },
  { key: "pickup", title: "Ready for pickup", statuses: ["ready_for_pickup"] },
  { key: "road", title: "On the road", statuses: ["picked_up", "in_transit"] },
  { key: "done", title: "Delivered", statuses: ["delivered", "received", "completed"] },
];

/** Groups for the vendor's order list. Covers every status a sold order can be in. */
export const VENDOR_ORDER_GROUPS: { key: string; title: string; statuses: VendorOrderStatus[] }[] = [
  { key: "confirm", title: "To confirm", statuses: ["paid"] },
  { key: "prepare", title: "To prepare", statuses: ["confirmed", "processing"] },
  { key: "pickup", title: "Waiting for pickup", statuses: ["ready_for_pickup"] },
  { key: "road", title: "On the road", statuses: ["picked_up", "in_transit"] },
  { key: "done", title: "Done", statuses: ["delivered", "received", "completed"] },
  { key: "closed", title: "Cancelled", statuses: ["cancelled", "refunded"] },
];

/** Used until the vendor's own low-stock level has loaded (the backend default too). */
export const DEFAULT_LOW_STOCK_THRESHOLD = 10;
