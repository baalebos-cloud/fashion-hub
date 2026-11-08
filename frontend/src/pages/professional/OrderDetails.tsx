import { useParams } from "react-router-dom";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { DispatchOffers } from "@/components/dispatch/DispatchOffers";
import { DeliveryJourney } from "@/components/dispatch/DeliveryJourney";
import { PickupCodeCard } from "@/components/dispatch/PickupCodeCard";
import { useState } from "react";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderItems } from "@/components/orders/OrderItems";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { OrderActions } from "@/components/orders/OrderActions";
import { OrderMaterials } from "@/components/orders/OrderMaterials";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { formatCurrency } from "@/lib/formatters/currency";
import type { CustomerOrderStatus } from "@/types/order";
import { PROFESSIONAL_ORDER_NEXT_STEP } from "@/constants/order-status";
import { Badge } from "@/components/ui/badge";

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, accept, startProduction, markReady, ship, markReceived } = useOrder(orderId);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<string | null>(null);
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  const [dispatchRefresh, setDispatchRefresh] = useState(0);

  async function dispatch() {
    if (!orderId) return;
    setDispatching(true);
    setDispatchError(null);
    try {
      const request = await deliveryRequestsApi.requestForOrder(orderId);
      setDispatchResult(request.status === "requested"
        ? "Riders nearby can now accept your job or send fare offers below."
        : "Courier request " + request.status + ".");
      setDispatchRefresh((n) => n + 1);
    } catch (err) {
      setDispatchError(getDisplayErrorMessage(err));
    } finally {
      setDispatching(false);
    }
  }

  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <OrderStatusBadge status={order.status as CustomerOrderStatus} />
          <span className="font-mono text-sm text-ink-soft">{order.order_number}</span>
        </div>
        <h1 className="font-display text-3xl text-ink">{order.items[0]?.name_snapshot ?? order.order_number}</h1>
        <p className="text-sm text-ink-soft">
          {order.ordered_at && <>Placed <DateTimeDisplay value={order.ordered_at} format="date" /> · </>}
          <span className="font-mono text-ink">{formatCurrency(order.total_amount, order.currency)}</span>
        </p>
      </header>

      {PROFESSIONAL_ORDER_NEXT_STEP[order.status as CustomerOrderStatus] && (
        <section aria-label="Next step" className="flex flex-col gap-3 rounded-card border border-indigo/30 bg-surface p-5">
          <p className="text-[13px] font-semibold uppercase tracking-wide text-ink-soft">Next step</p>
          <p className="font-semibold text-ink">{PROFESSIONAL_ORDER_NEXT_STEP[order.status as CustomerOrderStatus]}</p>
          <OrderActions
            order={order}
            onAccept={async () => { await accept(); }}
            onStartProduction={async () => { await startProduction(); }}
            onMarkReady={async () => { await markReady(); }}
            onShip={async () => { await ship(); }}
            onMarkReceived={async () => { await markReceived(); }}
          />
        </section>
      )}

      <section aria-label="Items" className="rounded-card border border-line bg-surface p-5">
        <OrderItems items={order.items} currency={order.currency} />
      </section>

      {order.order_type === "customer_order" && <OrderMaterials order={order} />}

      <section aria-label="Customer measurements" className="flex flex-col gap-2 rounded-card border border-dashed border-line-strong bg-surface p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold text-ink">Customer measurements</h2>
          <Badge tone="info">Coming soon</Badge>
        </div>
        <p className="text-sm text-ink-soft">
          The customer chose a saved measurement profile for this order, but the values aren't shown to you here yet.
          Ask them in Messages for anything you need before cutting.
        </p>
      </section>
      {order.order_type === "customer_order" && ["ready_for_delivery", "shipped"].includes(order.status) && (
        <div className="flex flex-col gap-2">
          <Button className="self-start" disabled={dispatching} isLoading={dispatching} onClick={() => void dispatch()}>
            Request internal courier
          </Button>
          {dispatchResult && <p role="status" className="text-sm text-ink-soft">{dispatchResult}</p>}
          {dispatchError && <p role="alert" className="text-sm text-thread">{dispatchError}</p>}
        </div>
      )}

      {order.order_type === "customer_order" && (
        <DispatchOffers orderId={order.id} refreshKey={dispatchRefresh} onAssigned={() => setDispatchRefresh((n) => n + 1)} />
      )}
      {order.order_type === "customer_order" && ["ready_for_delivery", "shipped"].includes(order.status) && (
        <PickupCodeCard key={dispatchRefresh} orderId={order.id} />
      )}
      {order.order_type === "customer_order" && <DeliveryJourney key={dispatchRefresh} orderId={order.id} />}
      <OrderContacts orderId={order.id} />

      <section aria-label="Timeline" className="rounded-card border border-line bg-surface p-5">
        <h2 className="mb-3 font-semibold text-ink">Timeline</h2>
        <OrderTimeline entries={timeline} />
      </section>
    </div>
  );
}
