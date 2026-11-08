import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ordersApi } from "@/api/orders.api";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { vendorRoutes } from "@/config/routes.config";
import { VENDOR_ORDER_GROUPS, VENDOR_ORDER_NEXT_STEP } from "@/constants/order-status";
import { formatCurrency } from "@/lib/formatters/currency";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { cn } from "@/lib/utils/cn";
import type { Order, VendorOrderStatus } from "@/types/order";

/** Material orders grouped by what the vendor has to do, newest first in each group. */
export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [groupKey, setGroupKey] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(false);
    ordersApi.listAll({ perspective: "selling", order_type: "vendor_order" })
      .then((list) => { if (active) setOrders(list.filter((o) => o.order_type === "vendor_order")); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  const groups = VENDOR_ORDER_GROUPS.map((g) => ({ ...g, orders: orders.filter((o) => g.statuses.includes(o.status as VendorOrderStatus)) }));
  // Open on the first group with work in it, unless the vendor picked one.
  const selected = groups.find((g) => g.key === groupKey) ?? groups.find((g) => g.orders.length > 0) ?? groups[0];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-3xl text-ink">Orders</h1>
      {isLoading && <SkeletonRows rows={4} label="Loading your orders" onRetry={() => setAttempt((n) => n + 1)} />}
      {!isLoading && error && (
        <ErrorState title="Couldn't load your orders" description="Check your connection, then try again." onRetry={() => setAttempt((n) => n + 1)} />
      )}
      {!isLoading && !error && (
        <>
          <div role="tablist" aria-label="Order groups" className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
            {groups.map((g) => (
              <button key={g.key} type="button" role="tab" aria-selected={g.key === selected.key} onClick={() => setGroupKey(g.key)}
                className={cn("flex min-h-11 shrink-0 items-center gap-2 rounded-full border px-4 text-sm font-semibold transition-colors",
                  g.key === selected.key ? "border-indigo bg-indigo-wash text-indigo" : "border-line-strong bg-surface text-ink hover:border-indigo")}>
                {g.title}<span className="font-mono text-xs">{g.orders.length}</span>
              </button>
            ))}
          </div>

          <section role="tabpanel" aria-label={selected.title}>
            {selected.orders.length === 0 ? (
              <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">
                {orders.length === 0 ? "No orders yet. When a tailor buys your materials, the order appears here." : `Nothing in "${selected.title}".`}
              </p>
            ) : (
              <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
                {selected.orders.map((order) => {
                  const next = VENDOR_ORDER_NEXT_STEP[order.status as VendorOrderStatus];
                  const first = order.items[0];
                  return (
                    <li key={order.id}>
                      <Link to={vendorRoutes.orderDetails(order.id)} className="grid gap-1.5 p-4 transition-colors hover:bg-paper sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                        <div className="flex min-w-0 flex-col gap-1">
                          <span className="font-mono text-xs text-ink-soft">
                            {order.order_number}{order.ordered_at && <> · <DateTimeDisplay value={order.ordered_at} format="date" /></>}
                          </span>
                          <span className="truncate font-semibold text-ink">
                            {first ? `${first.name_snapshot} × ${first.quantity}` : "Order"}
                            {order.items.length > 1 ? ` + ${order.items.length - 1} more` : ""}
                          </span>
                          {next && <span className="text-[13px] font-semibold text-indigo">{next}</span>}
                        </div>
                        <div className="flex items-center gap-3 sm:flex-col sm:items-end">
                          <OrderStatusBadge status={order.status} />
                          <span className="font-mono text-sm text-ink">{formatCurrency(order.total_amount, order.currency)}</span>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
