import { useMap } from "@/hooks/use-map";
import type { TrackingSnapshot } from "@/types/tracking";

/**
 * Placeholder map surface — swap the inner div for an actual Google Maps
 * / Mapbox GL marker render once useMap() confirms the SDK has loaded
 * (see lib/maps/map-client.ts). Coordinates come from the backend's
 * DeliveryTracking snapshot; this component never computes or guesses a
 * position itself.
 */
export function TrackingMap({ tracking }: { tracking: TrackingSnapshot | null }) {
  const { isReady } = useMap();

  return (
    <div className="flex h-64 items-center justify-center rounded-card border border-line bg-muslin text-sm text-ink-soft">
      {!isReady && "Loading map…"}
      {isReady && tracking?.current_latitude != null && (
        <span>
          Live position: {tracking.current_latitude.toFixed(4)}, {tracking.current_longitude?.toFixed(4)}
        </span>
      )}
      {isReady && tracking?.current_latitude == null && "Waiting for the first location update…"}
    </div>
  );
}
