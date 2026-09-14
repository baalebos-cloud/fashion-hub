import { useEffect } from "react";
import { useOrderStore } from "@/store/order.store";

/** Single-order detail hook (OrderDetails.tsx), exposing every lifecycle
 * action alongside the order itself so a detail page needs only this one
 * hook. */
export function useOrder(orderId: string | undefined) {
  const store = useOrderStore();

  useEffect(() => {
    if (orderId) {
      store.fetchById(orderId);
      store.fetchTimeline(orderId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  return {
    order: store.currentOrder,
    timeline: store.timeline,
    isLoading: store.isLoading,
    error: store.error,
    accept: () => orderId && store.accept(orderId),
    startProduction: () => orderId && store.startProduction(orderId),
    markReady: () => orderId && store.markReady(orderId),
    ship: () => orderId && store.ship(orderId),
    markReceived: () => orderId && store.markReceived(orderId),
    cancel: (note?: string) => orderId && store.cancel(orderId, note),
  };
}
