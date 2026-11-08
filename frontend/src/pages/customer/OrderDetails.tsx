import { useState } from "react";
import { useParams } from "react-router-dom";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { DeliveryJourney } from "@/components/dispatch/DeliveryJourney";
import { ShareTrackingCard } from "@/components/dispatch/ShareTrackingCard";
import { CustomerDeliveryTracking } from "@/components/delivery/CustomerDeliveryTracking";
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
import { CUSTOMER_ORDER_NEXT_STEP } from "@/constants/order-status";

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, error, markReceived } = useOrder(orderId);
  // Changes when a rider is assigned or replaced, so Contacts picks them up without a reload.
  const [riderKey, setRiderKey] = useState("");

  if (error) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <OrderStatusBadge status={order.status as CustomerOrderStatus} />
          <span className="font-mono text-sm text-ink-soft">{order.order_number}</span>
        </div>
        <h1 className="font-display text-3xl text-ink">{order.items[0]?.name_snapshot ?? order.order_number}</h1>
        {CUSTOMER_ORDER_NEXT_STEP[order.status as CustomerOrderStatus] && (
          <p className="text-[15px] text-ink">{CUSTOMER_ORDER_NEXT_STEP[order.status as CustomerOrderStatus]}</p>
        )}
        {order.ordered_at && (
          <p className="text-sm text-ink-soft">Placed <DateTimeDisplay value={order.ordered_at} format="date" /></p>
        )}
      </header>

      <section aria-label="Items" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-5">
        {order.items.length > 0 && <ul className="divide-y divide-line">
          {order.items.map((item) => <li key={item.id} className="flex justify-between gap-3 py-2 text-sm"><span>{item.name_snapshot} × {item.quantity}</span><span className="font-mono">{formatCurrency(item.line_total, order.currency)}</span></li>)}
        </ul>}
        <div className="flex justify-between gap-3 border-t border-line pt-2"><span className="font-semibold text-ink">Total</span><span className="font-mono text-lg font-semibold text-ink">{formatCurrency(order.total_amount, order.currency)}</span></div>
      </section>

      {order.order_type === "customer_order" && <DeliveryJourney orderId={order.id} />}
      {order.order_type === "customer_order" && ["ready_for_delivery", "shipped", "out_for_delivery", "delivered", "received", "completed"].includes(order.status) && (
        <ShareTrackingCard orderId={order.id} orderNumber={order.order_number}
          allowCreate={!["received", "completed"].includes(order.status)} />
      )}
      <OrderContacts orderId={order.id} refreshKey={riderKey} />
      {order.order_type === "customer_order" && <CustomerDeliveryTracking orderId={order.id} onRiderChange={setRiderKey} />}
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

      <section aria-label="Timeline" className="rounded-card border border-line bg-surface p-5">
        <h2 className="mb-3 font-semibold text-ink">Timeline</h2>
        <OrderTimeline entries={timeline} />
      </section>
    </div>
  );
}
