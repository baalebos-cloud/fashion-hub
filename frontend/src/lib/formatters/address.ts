import type { GeoLocation } from "@/types/location";

/** Renders a GeoLocation as a single display line, e.g. for order
 * summaries and delivery cards. Falls back gracefully when only partial
 * address components are available (common right after geocoding). */
export function formatAddressLine(location: Pick<GeoLocation, "formatted_address" | "city" | "state_region" | "country">): string {
  if (location.formatted_address) return location.formatted_address;
  return [location.city, location.state_region, location.country].filter(Boolean).join(", ");
}
