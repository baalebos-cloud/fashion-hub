import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { OrderStatusBadge } from "./OrderStatusBadge";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Order } from "@/types/order";
import type { CustomerOrderStatus } from "@/types/order";

export function OrderCard({ order, detailsPath }: { order: Order; detailsPath: string }) {
  return (
    <Link to={detailsPath}>
      <Card className="flex items-center justify-between transition-colors hover:border-brass">
        <div>
          <div className="font-medium text-ink">{order.order_number}</div>
          <div className="text-xs text-ink-soft">
            {order.ordered_at && <DateTimeDisplay value={order.ordered_at} format="date" />}
          </div>
        </div>
        <div className="text-right">
          <div className="mb-1 font-medium text-ink">{formatCurrency(order.total_amount, order.currency)}</div>
          <OrderStatusBadge status={order.status as CustomerOrderStatus} />
        </div>
      </Card>
    </Link>
  );
}
