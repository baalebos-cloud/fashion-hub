import { DeliveryMap } from "@/components/delivery/DeliveryMap";
import type { TrackingSnapshot } from "@/types/tracking";

/**
 * Where the rider is, from the backend's tracking snapshot (the rider's live sharing, or the last
 * courier ping). Shows the real map with a "View in Google Maps" link, which still works when the
 * embedded map can't load. Never computes or guesses a position itself.
 */
export function TrackingMap({ tracking }: { tracking: TrackingSnapshot | null }) {
  const hasPosition = tracking?.current_latitude != null && tracking.current_longitude != null;

  if (!hasPosition) {
    return (
      <div className="flex h-40 flex-col items-center justify-center gap-1 rounded-card border border-line bg-muslin p-4 text-center text-sm text-ink-soft">
        {tracking ? "Waiting for the rider's first location update…" : "The rider's location shows here once they pick up your order and share it."}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {tracking?.is_stale && (
        <p role="status" className="text-sm font-medium text-thread">
          Location updates are delayed. This is the last place the rider reported, not where they are now.
        </p>
      )}
      <DeliveryMap currentLat={tracking!.current_latitude} currentLng={tracking!.current_longitude} />
    </div>
  );
}
