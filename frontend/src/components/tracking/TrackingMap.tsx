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
  const { isReady, error } = useMap();

  return (
    <div className="flex h-64 flex-col items-center justify-center gap-1 rounded-card border border-line bg-muslin p-4 text-center text-sm text-ink-soft">
      {error && <span className="text-thread">{error}</span>}
      {!error && !isReady && "Loading map…"}
      {!error && isReady && tracking?.current_latitude != null && (
        <span>
          Live position: {tracking.current_latitude.toFixed(4)}, {tracking.current_longitude?.toFixed(4)}
        </span>
      )}
      {!error && isReady && tracking?.current_latitude == null && "Waiting for the first location update…"}
    </div>
  );
}
