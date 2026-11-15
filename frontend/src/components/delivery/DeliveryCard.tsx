import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { DeliveryStatusBadge } from "./DeliveryStatusBadge";
import { formatCurrency } from "@/lib/formatters/currency";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import type { Delivery, DeliveryStatus } from "@/types/delivery";

const UNPAID: ReadonlySet<DeliveryStatus> = new Set(["cancelled", "failed"]);

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
          {/* A cancelled or failed job isn't paid (see Earnings); active and delivered jobs keep their fare. */}
          <span className="text-sm text-ink-soft">{UNPAID.has(delivery.status) ? "No fare" : formatCurrency(delivery.delivery_fee)}</span>
          <DeliveryStatusBadge status={delivery.status} />
        </div>
      </Card>
    </Link>
  );
}
