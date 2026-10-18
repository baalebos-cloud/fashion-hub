import { Badge } from "@/components/ui/badge";
import { CUSTOMER_ORDER_STATUS_LABELS, VENDOR_ORDER_STATUS_LABELS, CUSTOMER_ORDER_STATUS_TONE, type StatusTone } from "@/constants/order-status";
import type { CustomerOrderStatus, VendorOrderStatus } from "@/types/order";

export function OrderStatusBadge({ status }: { status: CustomerOrderStatus | VendorOrderStatus }) {
  const labels: Partial<Record<CustomerOrderStatus | VendorOrderStatus, string>> = { ...VENDOR_ORDER_STATUS_LABELS, ...CUSTOMER_ORDER_STATUS_LABELS };
  const tones: Partial<Record<CustomerOrderStatus | VendorOrderStatus, StatusTone>> = CUSTOMER_ORDER_STATUS_TONE;
  return <Badge tone={tones[status] ?? "neutral"}>{labels[status] ?? status}</Badge>;
}
