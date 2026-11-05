import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Vendor } from "@/types/vendor";
import type { PaginatedResponse, PaginationParams } from "@/types/api";

export const vendorsApi = {
  /** Store pickup point riders collect materials from (new Location per save; old dispatches keep theirs). */
  async updateMyLocation(payload: { latitude: number; longitude: number; formattedAddress?: string | null;
    city?: string | null; stateRegion?: string | null; country?: string | null }): Promise<Vendor> {
    return (await apiClient.patch<Vendor>("/vendors/me/location", null, { params: {
      latitude: payload.latitude, longitude: payload.longitude, formatted_address: payload.formattedAddress ?? undefined,
      city: payload.city ?? undefined, state_region: payload.stateRegion ?? undefined, country: payload.country ?? undefined,
    } })).data;
  },
  async mine(): Promise<Vendor | null> { return (await apiClient.get<Vendor | null>(endpoints.vendors.mine)).data; },
  async create(payload: { business_name: string; business_description?: string }): Promise<Vendor> {
    return (await apiClient.post<Vendor>(endpoints.vendors.mine, payload)).data;
  },
  async list(params: PaginationParams = {}): Promise<PaginatedResponse<Vendor>> {
    const response = await apiClient.get<PaginatedResponse<Vendor>>(endpoints.vendors.list, { params });
    return response.data;
  },

  async getById(id: string): Promise<Vendor> {
    const response = await apiClient.get<Vendor>(endpoints.vendors.details(id));
    return response.data;
  },
};
