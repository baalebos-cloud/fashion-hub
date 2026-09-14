import { useEffect, useState } from "react";
import { ordersApi } from "@/api/orders.api";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import type { OrderTimelineEntry } from "@/types/order";

export function TrackingTimeline({ orderId }: { orderId: string }) {
  const [entries, setEntries] = useState<OrderTimelineEntry[]>([]);

  useEffect(() => {
    ordersApi.getTimeline(orderId).then(setEntries);
  }, [orderId]);

  return <OrderTimeline entries={entries} />;
}
