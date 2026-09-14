import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

/**
 * Geocoding ALWAYS goes through the backend (backend/app/integrations/maps/),
 * never called directly from the browser — this keeps the server-side maps
 * API key (which may have higher rate limits / billing implications) out
 * of client code entirely, and lets the backend apply its Redis cache
 * (see backend/docs/maps-and-gps.md).
 */
export interface GeocodeResult {
  latitude: number;
  longitude: number;
  formatted_address: string;
  city: string | null;
  state_region: string | null;
  country: string | null;
  postal_code: string | null;
}

export async function geocodeAddress(address: string): Promise<GeocodeResult> {
  const response = await apiClient.get<GeocodeResult>(endpoints.maps.geocode, { params: { address } });
  return response.data;
}

export async function reverseGeocode(latitude: number, longitude: number): Promise<GeocodeResult> {
  const response = await apiClient.get<GeocodeResult>(endpoints.maps.reverseGeocode, {
    params: { latitude, longitude },
  });
  return response.data;
}
