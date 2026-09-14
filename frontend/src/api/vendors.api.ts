import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Vendor } from "@/types/vendor";
import type { PaginatedResponse, PaginationParams } from "@/types/api";

export const vendorsApi = {
  async list(params: PaginationParams = {}): Promise<PaginatedResponse<Vendor>> {
    const response = await apiClient.get<PaginatedResponse<Vendor>>(endpoints.vendors.list, { params });
    return response.data;
  },

  async getById(id: string): Promise<Vendor> {
    const response = await apiClient.get<Vendor>(endpoints.vendors.details(id));
    return response.data;
  },
};
