import { useEffect, useRef } from "react";
import { useMap } from "@/hooks/use-map";

type Point = { lat: number; lng: number };
type MapsApi = {
  Map: new (element: HTMLElement, options: Record<string, unknown>) => unknown;
  Marker: new (options: Record<string, unknown>) => {
    setMap: (map: null) => void;
  };
};
type GoogleHost = Window & { google?: { maps?: MapsApi } };

export function DeliveryMap({ currentLat, currentLng }: {
  currentLat?: number | null;
  currentLng?: number | null;
}) {
  const { isReady, error } = useMap();
  const elementRef = useRef<HTMLDivElement>(null);
  const valid = currentLat != null && currentLng != null &&
    Number.isFinite(currentLat) && Number.isFinite(currentLng) &&
    Math.abs(currentLat) <= 90 && Math.abs(currentLng) <= 180;

  useEffect(() => {
    if (!isReady || !valid || !elementRef.current) return;
    const maps = (window as GoogleHost).google?.maps;
    if (!maps?.Map || !maps?.Marker) return;
    const position: Point = { lat: currentLat!, lng: currentLng! };
    const map = new maps.Map(elementRef.current, {
      center: position, zoom: 15, mapTypeControl: false, streetViewControl: false,
    });
    const marker = new maps.Marker({ map, position, title: "Rider's last reported position" });
    return () => marker.setMap(null);
  }, [isReady, valid, currentLat, currentLng]);

  if (!valid) return <p className="text-sm text-ink-soft">The rider has not reported a valid GPS point.</p>;
  const url = `https://www.google.com/maps/search/?api=1&query=${currentLat},${currentLng}`;
  return (
    <div className="space-y-2">
      <div ref={elementRef} role="application" aria-label="Last reported rider GPS position"
        className="h-64 w-full rounded-card border border-line bg-muslin"
        style={{ display: isReady && !error ? "block" : "none" }} />
      {(!isReady || error) && <p className="text-sm text-ink-soft">
        {error || "Loading location map…"}
      </p>}
      <a href={url} target="_blank" rel="noopener noreferrer" className="text-sm text-brass-deep underline">
        View reported position in Google Maps
      </a>
    </div>
  );
}
