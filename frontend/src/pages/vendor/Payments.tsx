import { useEffect, useState } from "react";
import { ordersApi } from "@/api/orders.api";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Order, VendorOrderStatus } from "@/types/order";
import { PayoutAccountForm } from "@/components/payouts/PayoutAccountForm";
import { SellerPayoutList } from "@/components/payouts/SellerPayoutList";

const NOT_SOLD: VendorOrderStatus[] = ["cart", "checkout", "payment_pending", "cancelled", "refunded"];

/** The vendor's payout account, their payouts, and the values of orders they've sold. */
export default function Payments() {
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

  const sold = orders.filter((o) => o.order_type === "vendor_order" && !NOT_SOLD.includes(o.status as VendorOrderStatus));
  const total = sold.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl text-ink">Payments</h1>
      </div>
      <p className="max-w-prose text-sm text-ink-soft">
        Once a buyer confirms they've received an order, Tailora sends your share (after its fee) to your bank account
        automatically. Add your account below to get paid.
      </p>
      <PayoutAccountForm />
      <SellerPayoutList />
      {isLoading && <SkeletonRows rows={3} label="Loading your orders" onRetry={() => setAttempt((n) => n + 1)} />}
      {!isLoading && error && <ErrorState title="Couldn't load your orders" description="Check your connection, then try again." onRetry={() => setAttempt((n) => n + 1)} />}
      {!isLoading && !error && sold.length === 0 && (
        <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">
          No paid orders yet. When a tailor pays for your materials, the order and its value are listed here.
        </p>
      )}
      {!isLoading && !error && sold.length > 0 && (
        <>
          <p className="text-sm text-ink-soft">
            {sold.length} order{sold.length === 1 ? "" : "s"} · total value <span className="font-mono font-semibold text-ink">{formatCurrency(total, sold[0].currency)}</span>
          </p>
          <div className="flex flex-col gap-3">
            {sold.map((order) => (
              <Card key={order.id} className="flex flex-wrap items-center justify-between gap-3">
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-semibold text-ink">{order.items[0]?.name_snapshot ?? order.order_number}</span>
                  <span className="font-mono text-xs text-ink-soft">{order.order_number}</span>
                </span>
                <span className="flex items-center gap-3">
                  <OrderStatusBadge status={order.status} />
                  <span className="font-mono text-sm text-ink">{formatCurrency(order.total_amount, order.currency)}</span>
                </span>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
