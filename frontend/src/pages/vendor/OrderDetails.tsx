import { useState } from "react";
import { useParams } from "react-router-dom";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { RequestRiderPanel } from "@/components/dispatch/RequestRiderPanel";
import { DeliveryJourney } from "@/components/dispatch/DeliveryJourney";
import { PickupCodeCard } from "@/components/dispatch/PickupCodeCard";
import { vendorRoutes } from "@/config/routes.config";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { OrderItems } from "@/components/orders/OrderItems";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { VENDOR_FULFILMENT_STEPS, VENDOR_ORDER_NEXT_STEP } from "@/constants/order-status";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { cn } from "@/lib/utils/cn";
import type { VendorOrderStatus } from "@/types/order";

const ACTION: Partial<Record<VendorOrderStatus, { status: "confirmed" | "processing" | "ready_for_pickup"; label: string; help: string }>> = {
  paid: { status: "confirmed", label: "Confirm and start preparing", help: "Check you have everything in this order before confirming." },
  confirmed: { status: "processing", label: "Start preparing", help: "Cut, pack and label the materials." },
  processing: { status: "ready_for_pickup", label: "Mark ready for pickup", help: "Once it's packed, request a rider on the next step." },
};
const DELIVERY_STATUSES = ["ready_for_pickup", "picked_up", "in_transit", "delivered", "received", "completed"];

/** One material order: where it is, the one thing to do next, then pickup, buyer and history. */
export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, error, vendorFulfillment } = useOrder(orderId);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (error && !order) return <ErrorState title="Couldn't load this order" description={error} />;
  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  const status = order.status as VendorOrderStatus;
  const action = order.order_type === "vendor_order" ? ACTION[status] : undefined;
  const next = VENDOR_ORDER_NEXT_STEP[status];
  const currentStep = VENDOR_FULFILMENT_STEPS.findIndex((s) => s.statuses.includes(status));
  const closed = status === "cancelled" || status === "refunded";
  const first = order.items[0];

  async function advance(target: "confirmed" | "processing" | "ready_for_pickup") {
    setActionError(null);
    setSubmitting(true);
    try {
      await vendorFulfillment(target);
    } catch (err) {
      setActionError(getDisplayErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <OrderStatusBadge status={order.status} />
          <span className="font-mono text-sm text-ink-soft">{order.order_number}</span>
        </div>
        <h1 className="font-display text-3xl text-ink">
          {first ? `${first.name_snapshot} × ${first.quantity}` : order.order_number}
          {order.items.length > 1 && <span className="text-ink-soft"> + {order.items.length - 1} more</span>}
        </h1>
        <p className="text-sm text-ink-soft">
          {order.ordered_at && <>Ordered <DateTimeDisplay value={order.ordered_at} format="date" /> · </>}
          <span className="font-mono text-ink">{formatCurrency(order.total_amount, order.currency)}</span>
        </p>
      </header>

      {!closed && currentStep >= 0 && (
        <ol aria-label="Fulfilment progress" className="grid grid-cols-3 gap-x-3 gap-y-4 rounded-card border border-line bg-surface p-4 sm:grid-cols-6">
          {VENDOR_FULFILMENT_STEPS.map((step, i) => (
            <li key={step.key} aria-current={i === currentStep ? "step" : undefined} className="flex min-w-0 flex-col gap-1.5 text-[13px]">
              <span className={cn("h-1.5 rounded-full", i < currentStep ? "bg-success" : i === currentStep ? "bg-indigo" : "bg-line")} />
              <span className={cn(i === currentStep ? "font-semibold text-ink" : "text-ink-soft")}>{step.title}</span>
            </li>
          ))}
        </ol>
      )}

      {next && (
        <section aria-label="Next step" className="flex flex-col gap-3 rounded-card border border-indigo/30 bg-surface p-5">
          <p className="text-[13px] font-semibold uppercase tracking-wide text-ink-soft">Next step</p>
          <p className="font-semibold text-ink">{next}</p>
          {action && <p className="text-sm text-ink-soft">{action.help}</p>}
          {action && (
            <Button className="self-start" disabled={submitting} isLoading={submitting} onClick={() => void advance(action.status)}>
              {action.label}
            </Button>
          )}
          {actionError && <p role="alert" className="text-sm text-thread">{actionError}</p>}
          {status === "paid" && (
            <p className="text-[13px] text-ink-soft">
              Short on stock? Message the buyer below before confirming. Declining a paid order needs refunds, which aren't switched on yet.
            </p>
          )}
        </section>
      )}

      {status === "ready_for_pickup" && <RequestRiderPanel orderId={order.id} pickupSettingsPath={vendorRoutes.delivery} />}
      {status === "ready_for_pickup" && <PickupCodeCard orderId={order.id} />}
      {DELIVERY_STATUSES.includes(status) && <DeliveryJourney orderId={order.id} />}

      <section aria-label="Items" className="rounded-card border border-line bg-surface p-5">
        <h2 className="mb-3 font-semibold text-ink">Items</h2>
        <OrderItems items={order.items} currency={order.currency} />
      </section>

      <OrderContacts orderId={order.id} />

      <section aria-label="Fulfilment history" className="rounded-card border border-line bg-surface p-5">
        <h2 className="mb-3 font-semibold text-ink">Fulfilment history</h2>
        <OrderTimeline entries={timeline} />
      </section>
    </div>
  );
}
