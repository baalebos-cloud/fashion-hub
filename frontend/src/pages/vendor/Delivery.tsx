import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ordersApi } from "@/api/orders.api";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { vendorRoutes } from "@/config/routes.config";
import { VendorPickupLocation } from "@/components/dispatch/VendorPickupLocation";
import type { Order } from "@/types/order";

const OUTBOUND = ["ready_for_pickup", "picked_up", "in_transit"];

/** Where riders collect from, and every order waiting for or out with a rider. */
export default function Delivery() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true; setIsLoading(true); setError(false);
    ordersApi.listAll({ perspective: "selling", order_type: "vendor_order" })
      .then((list) => { if (active) setOrders(list); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  const outbound = orders.filter((o) => OUTBOUND.includes(o.status));

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <h1 className="font-display text-3xl text-ink">Deliveries</h1>
      <VendorPickupLocation />
      <section aria-label="Outgoing orders" className="flex flex-col gap-3">
        <h2 className="font-semibold text-ink">Waiting for pickup or on the road</h2>
        {isLoading && <SkeletonRows rows={2} label="Loading deliveries" onRetry={() => setAttempt((n) => n + 1)} />}
        {!isLoading && error && <ErrorState title="Couldn't load your orders" description="Check your connection, then try again." onRetry={() => setAttempt((n) => n + 1)} />}
        {!isLoading && !error && outbound.length === 0 && (
          <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">
            Nothing out for delivery. Orders you mark ready for pickup appear here.
          </p>
        )}
        {!isLoading && !error && outbound.length > 0 && (
          <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
            {outbound.map((order) => (
              <li key={order.id}>
                <Link to={order.status === "ready_for_pickup" ? vendorRoutes.orderDetails(order.id) : vendorRoutes.trackDelivery(order.id)}
                  className="flex flex-wrap items-center justify-between gap-3 p-4 transition-colors hover:bg-paper">
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate font-semibold text-ink">{order.items[0]?.name_snapshot ?? order.order_number}</span>
                    <span className="font-mono text-xs text-ink-soft">{order.order_number}</span>
                  </span>
                  <span className="flex items-center gap-3">
                    <OrderStatusBadge status={order.status} />
                    <span className="text-sm font-semibold text-indigo">{order.status === "ready_for_pickup" ? "Request a rider" : "Track"}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
