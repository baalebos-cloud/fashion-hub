import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ordersApi } from "@/api/orders.api";
import { useAuth } from "@/hooks/use-auth";
import { Greeting } from "@/components/common/Greeting";
import { ShareShopCard } from "@/components/storefront/ShareShopCard";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { professionalRoutes } from "@/config/routes.config";
import { PROFESSIONAL_ORDER_NEXT_STEP, WORKROOM_STAGES } from "@/constants/order-status";
import { formatCurrency } from "@/lib/formatters/currency";
import type { CustomerOrderStatus, Order } from "@/types/order";

const NOT_SOLD: CustomerOrderStatus[] = ["pending", "cancelled", "rejected", "refunded"];

function OrderTile({ order }: { order: Order }) {
  const status = order.status as CustomerOrderStatus;
  const next = PROFESSIONAL_ORDER_NEXT_STEP[status];
  return (
    <Link to={professionalRoutes.orderDetails(order.id)}
      className="flex flex-col gap-1.5 rounded-control border border-line bg-surface p-3 transition-colors hover:border-indigo">
      <span className="font-mono text-xs text-ink-soft">{order.order_number}</span>
      <span className="font-semibold text-ink">{order.items[0]?.name_snapshot ?? "Order"}</span>
      <span className="font-mono text-[13px] text-ink-soft">{formatCurrency(order.total_amount, order.currency)}</span>
      {status === "paid" && <Badge tone="warning" className="self-start">Waiting for you</Badge>}
      {next && status !== "paid" && <span className="text-[13px] font-semibold text-indigo">{next}</span>}
    </Link>
  );
}

/** The workroom: what needs the tailor now, then every order by stage. */
export default function Dashboard() {
  const { user } = useAuth();
  // Totals and stage counts need every order, not just the newest page, so fetch all pages.
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const refetch = () => setAttempt((n) => n + 1);
  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(false);
    ordersApi.listAll({ perspective: "selling", order_type: "customer_order" })
      .then((list) => { if (active) setOrders(list); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  const selling = orders.filter((o) => o.order_type === "customer_order" && (!user || o.seller_user_id === user.id));
  // Material purchases the tailor made, fetched from the buying side.
  const [purchases, setPurchases] = useState<Order[]>([]);
  useEffect(() => {
    let active = true;
    ordersApi.listAll({ perspective: "buying", order_type: "vendor_order" })
      .then((list) => { if (active) setPurchases(list); })
      .catch(() => { if (active) setPurchases([]); });
    return () => { active = false; };
  }, []);
  const numberById = new Map(selling.map((o) => [o.id, o.order_number]));
  const materials = purchases.filter((o) => !["completed", "cancelled", "refunded", "cart"].includes(o.status));
  const byStage = WORKROOM_STAGES.map((stage) => ({
    ...stage,
    orders: selling.filter((o) => stage.statuses.includes(o.status as CustomerOrderStatus)),
  }));
  const count = (key: string) => byStage.find((s) => s.key === key)?.orders.length ?? 0;
  const toAccept = selling.filter((o) => o.status === "paid").length;
  const toSend = selling.filter((o) => o.status === "ready_for_delivery").length;

  const now = new Date();
  const thisMonth = selling.filter((o) => {
    if (NOT_SOLD.includes(o.status as CustomerOrderStatus) || !o.accepted_at) return false;
    const accepted = new Date(o.accepted_at);
    return accepted.getFullYear() === now.getFullYear() && accepted.getMonth() === now.getMonth();
  });
  const orderValue = thisMonth.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <Greeting subtitle="Today in the workroom." />
        <div className="flex flex-wrap gap-2">
          <Link to={professionalRoutes.vendorMarketplace}><Button variant="secondary">Browse materials</Button></Link>
          {toAccept > 0 && <Link to={professionalRoutes.orders}><Button>Review {toAccept} new order{toAccept === 1 ? "" : "s"}</Button></Link>}
        </div>
      </div>

      {isLoading && <SkeletonRows rows={3} label="Loading your orders" onRetry={refetch} />}
      {!isLoading && error && <ErrorState title="Couldn't load your orders" description="Check your connection, then try again." onRetry={refetch} />}

      {!isLoading && !error && (
        <>
          {(toAccept > 0 || toSend > 0) && (
            <section aria-label="Needs attention" className="flex flex-col gap-2 rounded-card border border-thread/30 bg-surface p-4">
              <h2 className="font-semibold text-thread">Needs attention</h2>
              <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink">
                {toAccept > 0 && <li><Badge tone="warning">Reply</Badge> {toAccept} paid order{toAccept === 1 ? "" : "s"} waiting for you to accept</li>}
                {toSend > 0 && <li><Badge tone="info">Send</Badge> {toSend} order{toSend === 1 ? "" : "s"} ready for a rider</li>}
              </ul>
            </section>
          )}

          <section aria-label="At a glance" className="grid grid-cols-2 overflow-hidden rounded-card border border-line bg-surface sm:grid-cols-4">
            {[["New", count("new"), "Accept within 24 h"], ["Being made", count("accepted") + count("making"), "Accepted or in production"],
              ["Ready or on the road", count("ready") + count("delivery"), "Ready to send or with the rider"], ["Done", count("done"), "Received by customers"]].map(([label, value, hint], i) => (
              <div key={label as string} className={`flex flex-col gap-1 p-4 ${i > 0 ? "sm:border-l" : ""} ${i % 2 === 1 ? "border-l" : ""} ${i > 1 ? "border-t sm:border-t-0" : ""} border-line`}>
                <span className="text-[13px] text-ink-soft">{label}</span>
                <span className="font-display text-3xl text-ink">{value}</span>
                <span className="text-xs text-ink-soft">{hint}</span>
              </div>
            ))}
          </section>

          <section aria-label="Orders by stage" className="flex flex-col gap-3">
            <h2 className="font-display text-2xl text-ink">Orders by stage</h2>
            {selling.length === 0 ? (
              <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">
                No orders yet. Share your shop link below so customers can find your designs.
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                {byStage.map((stage) => (
                  <div key={stage.key} className="flex min-w-0 flex-col gap-2">
                    <p className="flex justify-between text-xs font-semibold uppercase tracking-wide text-ink-soft">
                      {stage.title}<span className="font-mono">{stage.orders.length}</span>
                    </p>
                    {stage.orders.slice(0, stage.key === "done" ? 3 : 8).map((order) => <OrderTile key={order.id} order={order} />)}
                    {stage.orders.length === 0 && <p className="rounded-control border border-dashed border-line p-3 text-xs text-ink-soft">Nothing here</p>}
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <section aria-label="Money this month" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-semibold text-ink">Money this month</h2>
                <Badge tone="neutral">Payments not switched on</Badge>
              </div>
              <dl className="flex flex-col text-sm">
                <div className="flex justify-between gap-3 py-1.5"><dt>Order value accepted</dt><dd className="font-mono font-semibold">{formatCurrency(orderValue)}</dd></div>
                {["Payments received", "Pending", "Platform charges"].map((row) => (
                  <div key={row} className="flex justify-between gap-3 border-t border-line py-1.5"><dt>{row}</dt><dd className="text-ink-soft">Not yet available</dd></div>
                ))}
                <div className="flex justify-between gap-3 border-t border-line py-1.5"><dt className="font-semibold">Payouts to you</dt><dd><Badge tone="neutral">Not switched on</Badge></dd></div>
              </dl>
              <p className="text-[13px] text-ink-soft">Only order value is real today: the total of orders you accepted this month. The other rows fill in once payments and payouts are switched on.</p>
            </section>

            <section aria-label="Materials on the way" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
              <div className="flex items-baseline justify-between gap-2">
                <h2 className="font-semibold text-ink">Materials on the way</h2>
                <Link to={professionalRoutes.vendorOrders} className="text-sm font-semibold text-indigo">Material orders</Link>
              </div>
              {materials.length === 0 && <p className="text-sm text-ink-soft">No material orders in progress.</p>}
              {materials.slice(0, 4).map((order) => (
                <Link key={order.id} to={professionalRoutes.vendorOrderDetails(order.id)} className="flex items-center justify-between gap-3 text-sm hover:text-indigo">
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate">{order.items[0]?.name_snapshot ?? order.order_number}</span>
                    {order.parent_customer_order_id && numberById.get(order.parent_customer_order_id) && (
                      <span className="font-mono text-xs text-ink-soft">for {numberById.get(order.parent_customer_order_id)}</span>
                    )}
                  </span>
                  <OrderStatusBadge status={order.status} />
                </Link>
              ))}
              <Link to={professionalRoutes.vendorMarketplace} className="text-sm font-semibold text-indigo">Browse the materials marketplace</Link>
            </section>
          </div>
        </>
      )}

      <ShareShopCard />
    </div>
  );
}
