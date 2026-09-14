import { useEffect, useState } from "react";
import { loadMapSdk } from "@/lib/maps/map-client";

/** Ensures the map SDK script is loaded before a component (MapLocationPicker,
 * TrackingMap, DeliveryMap) attempts to instantiate a map. */
export function useMap() {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMapSdk()
      .then(() => !cancelled && setIsReady(true))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  return { isReady, error };
}
