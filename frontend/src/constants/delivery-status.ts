import type { DeliveryStatus } from "@/types/delivery";

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, string> = {
  requested: "Requested",
  assigned: "Assigned",
  rejected: "Rejected",
  picked_up: "Picked Up",
  in_transit: "In Transit",
  out_for_delivery: "Out for Delivery",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
};
