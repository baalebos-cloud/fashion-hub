import { formatCurrency } from "@/lib/formatters/currency";
import type { OrderItem } from "@/types/order";

export function OrderItems({ items, currency }: { items: OrderItem[]; currency: string }) {
  return (
    <div className="divide-y divide-line rounded-card border border-line">
      {items.map((item) => (
        <div key={item.id} className="flex items-center justify-between px-4 py-3 text-sm">
          <div>
            <div className="text-ink">{item.name_snapshot}</div>
            <div className="text-ink-soft">Qty {item.quantity}</div>
          </div>
          <div className="font-medium text-ink">{formatCurrency(item.line_total, currency)}</div>
        </div>
      ))}
    </div>
  );
}
