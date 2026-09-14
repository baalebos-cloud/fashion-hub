import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { GeoLocation, LocationType } from "@/types/location";

export const locationsApi = {
  async create(payload: {
    latitude: number;
    longitude: number;
    locationType: LocationType;
    formattedAddress?: string;
  }): Promise<GeoLocation> {
    const response = await apiClient.post<GeoLocation>(endpoints.locations.create, {
      latitude: payload.latitude,
      longitude: payload.longitude,
      location_type: payload.locationType,
      formatted_address: payload.formattedAddress,
    });
    return response.data;
  },
};
