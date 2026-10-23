import { useEffect, useState } from "react";
import { trackingApi } from "@/api/tracking.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { OrderTrackingResponse } from "@/types/tracking";

const POLL_INTERVAL_MS = 15_000;

/** Fetch even completed orders once; poll only active orders. Suppress updates
 * from requests that finished after navigating to a different order. */
export function useTracking(orderId: string | undefined, isActive: boolean) {
  const [tracking, setTracking] = useState<OrderTrackingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setTracking(null);
    setError(null);
    setIsLoading(true);
    if (!orderId) {
      setError("Missing order ID.");
      setIsLoading(false);
      return () => { active = false; };
    }
    async function fetchOnce() {
      try {
        const response = await trackingApi.getForOrder(orderId!);
        if (active) {
          setTracking(response);
          setError(null);
        }
      } catch (err) {
        if (active) setError(getDisplayErrorMessage(err));
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void fetchOnce();
    const interval = isActive ? setInterval(() => { void fetchOnce(); }, POLL_INTERVAL_MS) : null;
    return () => {
      active = false;
      if (interval) clearInterval(interval);
    };
  }, [orderId, isActive]);

  return { tracking, error, isLoading };
}
