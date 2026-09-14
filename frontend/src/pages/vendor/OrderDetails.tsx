import { useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { formatCurrency } from "@/lib/formatters/currency";
import type { CustomerOrderStatus } from "@/types/order";

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading } = useOrder(orderId);

  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-start justify-between">
        <h1 className="font-display text-xl text-ink">{order.order_number}</h1>
        <OrderStatusBadge status={order.status as CustomerOrderStatus} />
      </div>
      <div className="text-lg font-medium text-ink">{formatCurrency(order.total_amount, order.currency)}</div>
      <OrderTimeline entries={timeline} />
    </div>
  );
}
