import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { DeliveryStatusBadge } from "./DeliveryStatusBadge";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Delivery } from "@/types/delivery";

export function DeliveryCard({ delivery, detailsPath }: { delivery: Delivery; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="flex items-center justify-between transition-colors hover:border-brass">
        <div className="text-sm text-ink">Order {delivery.order_id.slice(0, 8)}</div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-ink-soft">{formatCurrency(delivery.delivery_fee)}</span>
          <DeliveryStatusBadge status={delivery.status} />
        </div>
      </Card>
    </Link>
  );
}
