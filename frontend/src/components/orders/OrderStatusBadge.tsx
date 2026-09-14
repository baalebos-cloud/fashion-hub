import { Badge } from "@/components/ui/badge";
import { CUSTOMER_ORDER_STATUS_LABELS, CUSTOMER_ORDER_STATUS_TONE } from "@/constants/order-status";
import type { CustomerOrderStatus } from "@/types/order";

export function OrderStatusBadge({ status }: { status: CustomerOrderStatus }) {
  return <Badge tone={CUSTOMER_ORDER_STATUS_TONE[status]}>{CUSTOMER_ORDER_STATUS_LABELS[status]}</Badge>;
}
