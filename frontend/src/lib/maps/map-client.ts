import { mapConfig } from "@/config/map.config";

/**
 * Loads the map rendering SDK (Google Maps JS API or Mapbox GL) once and
 * caches the promise, so multiple components (MapLocationPicker,
 * TrackingMap, DeliveryMap) mounting independently don't each inject a
 * duplicate <script> tag. This client is display-only: geocoding and
 * distance calculations are server-side (see lib/maps/geocoding.ts,
 * distance.ts), which call the backend, not this SDK.
 */
let loadPromise: Promise<void> | null = null;

export function loadMapSdk(): Promise<void> {
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    if (mapConfig.provider === "google_maps") {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${mapConfig.publicKey}&libraries=places`;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Failed to load Google Maps SDK."));
      document.head.appendChild(script);
    } else {
      const script = document.createElement("script");
      script.src = "https://api.mapbox.com/mapbox-gl-js/v3.7.0/mapbox-gl.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Failed to load Mapbox GL SDK."));
      document.head.appendChild(script);
    }
  });

  return loadPromise;
}
