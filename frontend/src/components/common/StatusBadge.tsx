import { Badge } from "@/components/ui/badge";
import { CUSTOMER_ORDER_STATUS_LABELS, CUSTOMER_ORDER_STATUS_TONE } from "@/constants/order-status";
import type { CustomerOrderStatus } from "@/types/order";

/** Generic order-status pill — OrderStatusBadge (components/orders/) wraps
 * this with order-specific context; this version is reused anywhere else
 * a bare status needs rendering (e.g. admin tables). */
export function StatusBadge({ status }: { status: CustomerOrderStatus }) {
  return <Badge tone={CUSTOMER_ORDER_STATUS_TONE[status]}>{CUSTOMER_ORDER_STATUS_LABELS[status]}</Badge>;
}
