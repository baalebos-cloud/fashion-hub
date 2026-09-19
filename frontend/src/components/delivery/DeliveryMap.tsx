import { useMap } from "@/hooks/use-map";

export function DeliveryMap({ currentLat, currentLng }: { currentLat?: number | null; currentLng?: number | null }) {
  const { isReady, error } = useMap();

  return (
    <div className="flex h-64 flex-col items-center justify-center gap-1 rounded-card border border-line bg-muslin p-4 text-center text-sm text-ink-soft">
      {error && <span className="text-thread">{error}</span>}
      {!error && !isReady && "Loading map…"}
      {!error && isReady && currentLat != null && <span>Current position: {currentLat.toFixed(4)}, {currentLng?.toFixed(4)}</span>}
      {!error && isReady && currentLat == null && "No position reported yet"}
    </div>
  );
}
