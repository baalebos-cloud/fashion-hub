import { useEffect, useRef, useState } from "react";
import { trackingApi } from "@/api/tracking.api";
import type { OrderTrackingResponse } from "@/types/tracking";

const POLL_INTERVAL_MS = 15_000;

/** Polls tracking for an order while it's active. A production build
 * should prefer a WebSocket subscription (see backend's real-time
 * guidance) — polling is kept here as the zero-infra default so tracking
 * works even before that's wired up. */
export function useTracking(orderId: string | undefined, isActive: boolean) {
  const [tracking, setTracking] = useState<OrderTrackingResponse | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (!orderId || !isActive) return;

    const fetchOnce = () => {
      trackingApi.getForOrder(orderId).then(setTracking).catch(() => {});
    };

    fetchOnce();
    intervalRef.current = setInterval(fetchOnce, POLL_INTERVAL_MS);
    return () => clearInterval(intervalRef.current);
  }, [orderId, isActive]);

  return { tracking };
}
