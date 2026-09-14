import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Professional } from "@/types/professional";
import type { Design } from "@/types/design";
import type { VendorProduct } from "@/types/product";

export const searchApi = {
  async professionals(query: string): Promise<Professional[]> {
    const response = await apiClient.get<Professional[]>(endpoints.search.professionals, { params: { q: query } });
    return response.data;
  },

  async designs(query: string): Promise<Design[]> {
    const response = await apiClient.get<Design[]>(endpoints.search.designs, { params: { q: query } });
    return response.data;
  },

  async vendorProducts(query: string): Promise<VendorProduct[]> {
    const response = await apiClient.get<VendorProduct[]>(endpoints.search.products, { params: { q: query } });
    return response.data;
  },
};
