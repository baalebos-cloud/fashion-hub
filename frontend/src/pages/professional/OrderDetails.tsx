import { useParams } from "react-router-dom";
import { useState } from "react";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderItems } from "@/components/orders/OrderItems";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { OrderActions } from "@/components/orders/OrderActions";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { formatCurrency } from "@/lib/formatters/currency";
import type { CustomerOrderStatus } from "@/types/order";

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, accept, startProduction, markReady, ship, markReceived } = useOrder(orderId);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<string | null>(null);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  async function dispatch() {
    if (!orderId) return;
    setDispatching(true);
    setDispatchError(null);
    try {
      const request = await deliveryRequestsApi.requestForOrder(orderId);
      setDispatchResult("Courier request " + request.status + ". Verified couriers can claim it in their dashboard.");
    } catch (err) {
      setDispatchError(getDisplayErrorMessage(err));
    } finally {
      setDispatching(false);
    }
  }

  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-xl text-ink">{order.order_number}</h1>
          {order.ordered_at && <p className="text-sm text-ink-soft">Placed <DateTimeDisplay value={order.ordered_at} format="date" /></p>}
        </div>
        <OrderStatusBadge status={order.status as CustomerOrderStatus} />
      </div>

      <div className="text-lg font-medium text-ink">{formatCurrency(order.total_amount, order.currency)}</div>

      <OrderActions
        order={order}
        onAccept={async () => { await accept(); }}
        onStartProduction={async () => { await startProduction(); }}
        onMarkReady={async () => { await markReady(); }}
        onShip={async () => { await ship(); }}
        onMarkReceived={async () => { await markReceived(); }}
      />

      <OrderItems items={order.items} currency={order.currency} />
      {order.order_type === "customer_order" && ["ready_for_delivery", "shipped"].includes(order.status) && (
        <div className="flex flex-col gap-2">
          <Button className="self-start" disabled={dispatching} isLoading={dispatching} onClick={() => void dispatch()}>
            Request internal courier
          </Button>
          {dispatchResult && <p role="status" className="text-sm text-ink-soft">{dispatchResult}</p>}
          {dispatchError && <p role="alert" className="text-sm text-thread">{dispatchError}</p>}
        </div>
      )

      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Timeline</h2>
        <OrderTimeline entries={timeline} />
      </div>
    </div>
  );
}
