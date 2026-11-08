import { useOrders } from "@/hooks/use-orders";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { formatCurrency } from "@/lib/formatters/currency";
import { EmptyState } from "@/components/ui/empty-state";
import type { CustomerOrderStatus } from "@/types/order";

const NOT_SOLD: CustomerOrderStatus[] = ["pending", "cancelled", "rejected", "refunded"];

/** Order values only. Online payments and payouts aren't switched on, so nothing here claims
 * money was received or paid out. */
export default function Payments() {
  const { orders } = useOrders();
  const sold = orders.filter((o) => o.order_type === "customer_order" && !NOT_SOLD.includes(o.status as CustomerOrderStatus));

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl text-ink">Payments</h1>
        <Badge tone="neutral">Payments and payouts not switched on</Badge>
      </div>
      <p className="max-w-prose text-sm text-ink-soft">
        These are the values of orders you've accepted. Received amounts, platform charges and payouts appear here once
        online payments and payouts are switched on.
      </p>
      {sold.length === 0 ? <EmptyState title="No accepted orders yet" description="Orders you accept will be listed here with their value." /> : (
        <div className="flex flex-col gap-3">
          {sold.map((order) => (
            <Card key={order.id} className="flex flex-wrap items-center justify-between gap-3">
              <span className="flex flex-col">
                <span className="font-semibold text-ink">{order.items[0]?.name_snapshot ?? order.order_number}</span>
                <span className="font-mono text-xs text-ink-soft">{order.order_number}</span>
              </span>
              <span className="flex items-center gap-3">
                <OrderStatusBadge status={order.status} />
                <span className="font-mono text-sm text-ink">{formatCurrency(order.total_amount, order.currency)}</span>
              </span>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
