import { env } from "./environment";

/**
 * Client-side map rendering config only. Geocoding/reverse-geocoding/
 * distance calculations are NEVER called directly from the browser —
 * they go through the backend's MapProvider abstraction
 * (see lib/maps/geocoding.ts), which is the only place a server-side maps
 * secret key is used. Only a public/restricted map-display key belongs
 * here.
 */
export const mapConfig = {
  provider: env.mapsProvider as "google_maps" | "mapbox",
  publicKey: env.mapsPublicKey,
  defaultCenter: { lat: 6.5244, lng: 3.3792 }, // Lagos, NG — sensible platform default
  defaultZoom: 12,
  nearbySearchRadiusKm: 10,
} as const;
