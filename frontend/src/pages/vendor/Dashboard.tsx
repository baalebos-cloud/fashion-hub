import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ordersApi } from "@/api/orders.api";
import { inventoryApi } from "@/api/inventory.api";
import { Greeting } from "@/components/common/Greeting";
import { ShareShopCard } from "@/components/storefront/ShareShopCard";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { vendorRoutes } from "@/config/routes.config";
import { VENDOR_ORDER_NEXT_STEP } from "@/constants/order-status";
import { useLowStockThreshold } from "@/hooks/use-low-stock-threshold";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Order, VendorOrderStatus } from "@/types/order";
import type { Inventory } from "@/types/product";

const OPEN: VendorOrderStatus[] = ["paid", "confirmed", "processing", "ready_for_pickup", "picked_up", "in_transit"];
const NOT_SOLD: VendorOrderStatus[] = ["cart", "checkout", "payment_pending", "cancelled", "refunded"];

function itemSummary(order: Order) {
  const first = order.items[0];
  if (!first) return "Order";
  const more = order.items.length > 1 ? ` + ${order.items.length - 1} more` : "";
  return `${first.name_snapshot} × ${first.quantity}${more}`;
}

/** The vendor's day: orders to confirm, prepare and hand over, stock running low, and this month's sales. */
export default function Dashboard() {
  // Counts and totals need every order, so fetch all pages rather than the newest 20.
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(false);
    ordersApi.listAll({ perspective: "selling", order_type: "vendor_order" })
      .then((list) => { if (active) setOrders(list); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  const [stock, setStock] = useState<Inventory[] | null>(null);
  useEffect(() => {
    let active = true;
    inventoryApi.listAll()
      .then((rows) => { if (active) setStock(rows); })
      .catch(() => { if (active) setStock(null); });
    return () => { active = false; };
  }, []);

  const sold = orders.filter((o) => o.order_type === "vendor_order");
  const withStatus = (...statuses: VendorOrderStatus[]) => sold.filter((o) => statuses.includes(o.status as VendorOrderStatus));
  const toConfirm = withStatus("paid");
  const toPrepare = withStatus("confirmed", "processing");
  const awaitingPickup = withStatus("ready_for_pickup");
  const onRoad = withStatus("picked_up", "in_transit");
  const open = withStatus(...OPEN).sort((a, b) => OPEN.indexOf(a.status as VendorOrderStatus) - OPEN.indexOf(b.status as VendorOrderStatus));

  const { threshold } = useLowStockThreshold();
  const low = (stock ?? []).filter((row) => row.quantity_available <= threshold)
    .sort((a, b) => a.quantity_available - b.quantity_available);

  const now = new Date();
  const thisMonth = sold.filter((o) => {
    const when = o.paid_at ?? o.ordered_at;
    if (NOT_SOLD.includes(o.status as VendorOrderStatus) || !when) return false;
    const paid = new Date(when);
    return paid.getFullYear() === now.getFullYear() && paid.getMonth() === now.getMonth();
  });
  const salesValue = thisMonth.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <Greeting subtitle="Today at your shop." />
        <div className="flex flex-wrap gap-2">
          <Link to={vendorRoutes.addProduct}><Button variant="secondary">Add product</Button></Link>
          {toConfirm.length > 0 && (
            <Link to={vendorRoutes.orders}><Button>Confirm {toConfirm.length} new order{toConfirm.length === 1 ? "" : "s"}</Button></Link>
          )}
        </div>
      </div>

      {isLoading && <SkeletonRows rows={3} label="Loading your orders" onRetry={() => setAttempt((n) => n + 1)} />}
      {!isLoading && error && (
        <ErrorState title="Couldn't load your orders" description="Check your connection, then try again." onRetry={() => setAttempt((n) => n + 1)} />
      )}

      {!isLoading && !error && (
        <>
          <section aria-label="At a glance" className="grid grid-cols-2 overflow-hidden rounded-card border border-line bg-surface sm:grid-cols-4">
            {([
              ["New orders", toConfirm.length, "Confirm you have the stock"],
              ["To prepare", toPrepare.length, "Confirmed or being prepared"],
              ["Waiting for pickup", awaitingPickup.length, "Ready for a rider"],
              ["On the road", onRoad.length, "With a rider"],
            ] as const).map(([label, value, hint], i) => (
              <div key={label} className={`flex flex-col gap-1 border-line p-4 ${i > 0 ? "sm:border-l" : ""} ${i % 2 === 1 ? "border-l" : ""} ${i > 1 ? "border-t sm:border-t-0" : ""}`}>
                <span className="text-[13px] text-ink-soft">{label}</span>
                <span className="font-display text-3xl text-ink">{value}</span>
                <span className="text-xs text-ink-soft">{hint}</span>
              </div>
            ))}
          </section>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <section aria-label="Orders to handle" className="flex flex-col gap-3">
              <div className="flex items-baseline justify-between">
                <h2 className="font-display text-2xl text-ink">Orders to handle</h2>
                <Link to={vendorRoutes.orders} className="text-sm font-semibold text-indigo">All orders</Link>
              </div>
              {open.length === 0 ? (
                <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">
                  Nothing to handle right now. New material orders from tailors appear here.
                </p>
              ) : (
                <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
                  {open.slice(0, 8).map((order) => {
                    const next = VENDOR_ORDER_NEXT_STEP[order.status as VendorOrderStatus];
                    return (
                      <li key={order.id}>
                        <Link to={vendorRoutes.orderDetails(order.id)}
                          className="flex flex-wrap items-center gap-x-4 gap-y-1.5 p-4 transition-colors hover:bg-paper">
                          <span className="font-mono text-xs text-ink-soft">{order.order_number}</span>
                          <span className="min-w-0 flex-1 truncate font-semibold text-ink">{itemSummary(order)}</span>
                          <OrderStatusBadge status={order.status} />
                          {next && <span className="w-full text-[13px] font-semibold text-indigo sm:w-auto">{next}</span>}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <div className="flex flex-col gap-6">
              <section aria-label="Low on stock" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
                <div className="flex items-baseline justify-between">
                  <h2 className="font-semibold text-ink">Low on stock</h2>
                  <Link to={vendorRoutes.inventory} className="text-sm font-semibold text-indigo">Restock</Link>
                </div>
                {stock === null && <p className="text-sm text-ink-soft">Stock levels couldn't be loaded.</p>}
                {stock !== null && low.length === 0 && <p className="text-sm text-ink-soft">Everything has more than {threshold} in stock.</p>}
                {low.length > 0 && (
                  <ul className="flex flex-col gap-2">
                    {low.slice(0, 5).map((row) => (
                      <li key={row.id} className="flex items-center justify-between gap-3 text-sm">
                        <span className="min-w-0 truncate text-ink">{row.product_name ?? row.sku}</span>
                        <span className="flex shrink-0 items-center gap-2">
                          <span className="font-mono text-ink-soft">{row.quantity_available}</span>
                          {row.quantity_available === 0 ? <Badge tone="danger">Out</Badge> : <Badge tone="warning">Low</Badge>}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section aria-label="Sales this month" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="font-semibold text-ink">Sales this month</h2>
                  <Badge tone="neutral">Payouts not switched on</Badge>
                </div>
                <p className="font-mono text-2xl font-semibold text-ink">{formatCurrency(salesValue, sold[0]?.currency ?? "NGN")}</p>
                <p className="text-[13px] text-ink-soft">
                  Value of {thisMonth.length} paid order{thisMonth.length === 1 ? "" : "s"} this month, before any platform charges.
                  Payouts start once they're switched on.
                </p>
              </section>
            </div>
          </div>
        </>
      )}

      <ShareShopCard />
    </div>
  );
}
