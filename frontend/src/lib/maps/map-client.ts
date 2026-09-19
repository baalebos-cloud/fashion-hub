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

  if (!mapConfig.publicKey) {
    // Fail fast with a clear message rather than loading a Google/Mapbox
    // script with an empty key — that fails silently in the browser
    // console with a cryptic provider-side error instead of telling
    // whoever's debugging that VITE_MAPS_PUBLIC_KEY is unset.
    loadPromise = Promise.reject(
      new Error("VITE_MAPS_PUBLIC_KEY is not set — see .env.example for how to get one.")
    );
    return loadPromise;
  }

  loadPromise = new Promise((resolve, reject) => {
    if (mapConfig.provider === "google_maps") {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${mapConfig.publicKey}&libraries=places`;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Failed to load Google Maps SDK — check that VITE_MAPS_PUBLIC_KEY is valid and the Maps JavaScript API is enabled."));
      document.head.appendChild(script);
    } else {
      const script = document.createElement("script");
      script.src = "https://api.mapbox.com/mapbox-gl-js/v3.7.0/mapbox-gl.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Failed to load Mapbox GL SDK — check that VITE_MAPS_PUBLIC_KEY is a valid Mapbox token."));
      document.head.appendChild(script);
    }
  });

  return loadPromise;
}
