import { useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderItems } from "@/components/orders/OrderItems";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { MarkReceivedButton } from "@/components/orders/MarkReceivedButton";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { formatCurrency } from "@/lib/formatters/currency";
import type { CustomerOrderStatus } from "@/types/order";

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, markReceived } = useOrder(orderId);

  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-xl text-ink">{order.order_number}</h1>
          {order.ordered_at && (
            <p className="text-sm text-ink-soft">
              Placed <DateTimeDisplay value={order.ordered_at} format="date" />
            </p>
          )}
        </div>
        <OrderStatusBadge status={order.status as CustomerOrderStatus} />
      </div>

      <div className="text-lg font-medium text-ink">{formatCurrency(order.total_amount, order.currency)}</div>

      <MarkReceivedButton order={order} onConfirm={markReceived} />

      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Timeline</h2>
        <OrderTimeline entries={timeline} />
      </div>
    </div>
  );
}
