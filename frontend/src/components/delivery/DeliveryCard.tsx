import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { DeliveryStatusBadge } from "./DeliveryStatusBadge";
import { formatCurrency } from "@/lib/formatters/currency";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import type { Delivery } from "@/types/delivery";

export function DeliveryCard({ delivery, detailsPath }: { delivery: Delivery; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="flex items-center justify-between transition-colors hover:border-brass">
        <div className="flex flex-col">
          <span className="text-sm text-ink">Order {delivery.order_id.slice(0, 8).toUpperCase()}</span>
          {delivery.delivered_at && (
            <span className="text-xs text-ink-soft">Delivered <DateTimeDisplay value={delivery.delivered_at} format="datetime" /></span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Only delivered jobs are paid (see Earnings), so a cancelled or failed job shows no fare. */}
          <span className="text-sm text-ink-soft">{delivery.status === "delivered" ? formatCurrency(delivery.delivery_fee) : "No fare"}</span>
          <DeliveryStatusBadge status={delivery.status} />
        </div>
      </Card>
    </Link>
  );
}
