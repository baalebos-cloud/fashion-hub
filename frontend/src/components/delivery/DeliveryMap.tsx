import { useMap } from "@/hooks/use-map";

export function DeliveryMap({ currentLat, currentLng }: { currentLat?: number | null; currentLng?: number | null }) {
  const { isReady } = useMap();

  return (
    <div className="flex h-64 items-center justify-center rounded-card border border-line bg-muslin text-sm text-ink-soft">
      {!isReady && "Loading map…"}
      {isReady && currentLat != null && <span>Current position: {currentLat.toFixed(4)}, {currentLng?.toFixed(4)}</span>}
      {isReady && currentLat == null && "No position reported yet"}
    </div>
  );
}
