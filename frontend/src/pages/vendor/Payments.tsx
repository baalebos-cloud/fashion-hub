import { useOrders } from "@/hooks/use-orders";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";
import { EmptyState } from "@/components/ui/empty-state";

export default function Payments() {
  const { orders } = useOrders();
  const paid = orders.filter((o) => o.status !== "cart" && o.status !== "checkout" && o.status !== "payment_pending");

  if (paid.length === 0) return <EmptyState title="No payments yet" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Payments received</h1>
      <div className="flex flex-col gap-3">
        {paid.map((order) => (
          <Card key={order.id} className="flex items-center justify-between">
            <span className="text-sm text-ink">{order.order_number}</span>
            <span className="text-sm text-ink-soft">{formatCurrency(order.total_amount, order.currency)}</span>
          </Card>
        ))}
      </div>
    </div>
  );
}
