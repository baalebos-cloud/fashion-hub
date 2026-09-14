import { Badge } from "@/components/ui/badge";
import { DELIVERY_STATUS_LABELS } from "@/constants/delivery-status";
import type { DeliveryStatus } from "@/types/delivery";

const TONE: Record<DeliveryStatus, "neutral" | "info" | "success" | "warning" | "danger"> = {
  requested: "neutral",
  assigned: "info",
  rejected: "danger",
  picked_up: "info",
  in_transit: "info",
  out_for_delivery: "info",
  delivered: "success",
  failed: "danger",
  cancelled: "danger",
};

export function DeliveryStatusBadge({ status }: { status: DeliveryStatus }) {
  return <Badge tone={TONE[status]}>{DELIVERY_STATUS_LABELS[status]}</Badge>;
}
