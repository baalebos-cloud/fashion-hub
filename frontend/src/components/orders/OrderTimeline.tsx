import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { CUSTOMER_ORDER_STATUS_LABELS } from "@/constants/order-status";
import type { OrderTimelineEntry, CustomerOrderStatus } from "@/types/order";

/** Renders the append-only history from GET /orders/{id}/timeline —
 * see backend/docs/orders.md. Every entry is server-authored, so this
 * component never re-derives or guesses a status from local state. */
export function OrderTimeline({ entries }: { entries: OrderTimelineEntry[] }) {
  return (
    <ol className="relative border-l border-line pl-5">
      {entries.map((entry, index) => (
        <li key={index} className="mb-5 last:mb-0">
          <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-brass" />
          <div className="text-sm font-medium text-ink">
            {CUSTOMER_ORDER_STATUS_LABELS[entry.to_status as CustomerOrderStatus] ?? entry.to_status}
          </div>
          <div className="text-xs text-ink-soft">
            <DateTimeDisplay value={entry.created_at} format="datetime" />
          </div>
          {entry.note && <p className="mt-1 text-xs text-ink-soft">{entry.note}</p>}
        </li>
      ))}
    </ol>
  );
}
