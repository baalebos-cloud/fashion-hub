import { useEffect, useState } from "react";
import { weatherApi } from "@/api/weather.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { WeatherSnapshot } from "@/types/weather";

const REFRESH_INTERVAL_MS = 15 * 60 * 1000; // matches the backend's 15-minute Redis cache TTL

/** Weather at a specific order's delivery destination -- only meaningful
 * once the order actually has a delivery address, so pass `isActive` from
 * the same conditions TrackingPage already uses. */
export function useOrderWeather(orderId: string | undefined, isActive: boolean) {
  const [weather, setWeather] = useState<WeatherSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId || !isActive) return;

    let cancelled = false;
    const fetchOnce = () => {
      setIsLoading(true);
      weatherApi
        .getForOrder(orderId)
        .then((result) => !cancelled && setWeather(result))
        .catch((err) => !cancelled && setError(getDisplayErrorMessage(err, "Weather unavailable right now.")))
        .finally(() => !cancelled && setIsLoading(false));
    };

    fetchOnce();
    const interval = setInterval(fetchOnce, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [orderId, isActive]);

  return { weather, isLoading, error };
}
