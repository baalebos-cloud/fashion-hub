import { useParams } from "react-router-dom";
import { SandboxSagaStatus } from "@/components/orders/SandboxSagaStatus";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { MarkReceivedButton } from "@/components/orders/MarkReceivedButton";
import { ReviewForm } from "@/components/reviews/ReviewForm";
import { ordersApi } from "@/api/orders.api";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { formatCurrency } from "@/lib/formatters/currency";
import type { CustomerOrderStatus } from "@/types/order";

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, error, markReceived } = useOrder(orderId);

  if (error) return <p role="alert" className="text-thread">{error}</p>;
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

      {order.items.length > 0 && <ul className="divide-y divide-line">
        {order.items.map((item) => <li key={item.id} className="flex justify-between py-2 text-sm"><span>{item.name_snapshot} × {item.quantity}</span><span>{formatCurrency(item.line_total, order.currency)}</span></li>)}
      </ul>}
      <div className="text-lg font-medium text-ink">{formatCurrency(order.total_amount, order.currency)}</div>

      <SandboxSagaStatus orderId={order.id} />
      <MarkReceivedButton order={order} onConfirm={async () => { await markReceived(); }} />
      {order.order_type === "customer_order" && order.status === "completed" && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-ink-soft">Review your order</h2>
          <ReviewForm onSubmit={async (score, comment) => {
            await ordersApi.submitReview(order.id, score, comment);
          }} />
        </section>
      )}

      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Timeline</h2>
        <OrderTimeline entries={timeline} />
      </div>
    </div>
  );
}
