import { useState } from "react";
import { useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { OrderItems } from "@/components/orders/OrderItems";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { VendorOrderStatus } from "@/types/order";

const nextStep: Partial<Record<VendorOrderStatus, {
  status: "confirmed" | "processing" | "ready_for_pickup";
  label: string;
}>> = {
  paid: { status: "confirmed", label: "Confirm material order" },
  confirmed: { status: "processing", label: "Begin preparing materials" },
  processing: { status: "ready_for_pickup", label: "Mark ready for pickup" },
};

export default function OrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, error, vendorFulfillment } = useOrder(orderId);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (error && !order) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  const action = order.order_type === "vendor_order" ? nextStep[order.status as VendorOrderStatus] : undefined;

  async function advance(status: "confirmed" | "processing" | "ready_for_pickup") {
    setActionError(null);
    setSubmitting(true);
    try {
      await vendorFulfillment(status);
    } catch (err) {
      setActionError(getDisplayErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-start justify-between">
        <h1 className="font-display text-xl text-ink">{order.order_number}</h1>
        <OrderStatusBadge status={order.status} />
      </div>
      <div className="text-lg font-medium text-ink">{formatCurrency(order.total_amount, order.currency)}</div>
      <OrderItems items={order.items} currency={order.currency} />
      {action && <Button disabled={submitting} isLoading={submitting}
        onClick={() => advance(action.status)}>{action.label}</Button>}
      {actionError && <p role="alert" className="text-sm text-thread">{actionError}</p>}
      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Fulfillment history</h2>
        <OrderTimeline entries={timeline} />
      </div>
    </div>
  );
}
