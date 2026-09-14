import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { VendorProduct } from "@/types/product";
import type { PaginatedResponse, PaginationParams } from "@/types/api";

export interface ProductCreatePayload {
  name: string;
  description?: string;
  base_price: number;
  category_id?: string;
}

export const productsApi = {
  async list(params: PaginationParams & { vendorId?: string; categoryId?: string } = {}): Promise<
    PaginatedResponse<VendorProduct>
  > {
    const response = await apiClient.get<PaginatedResponse<VendorProduct>>(endpoints.vendorProducts.list, {
      params: { vendor_id: params.vendorId, category_id: params.categoryId, page: params.page, page_size: params.pageSize },
    });
    return response.data;
  },

  async getById(id: string): Promise<VendorProduct> {
    const response = await apiClient.get<VendorProduct>(endpoints.vendorProducts.details(id));
    return response.data;
  },

  async create(payload: ProductCreatePayload): Promise<VendorProduct> {
    const response = await apiClient.post<VendorProduct>(endpoints.vendorProducts.list, payload);
    return response.data;
  },

  async update(id: string, payload: Partial<ProductCreatePayload>): Promise<VendorProduct> {
    const response = await apiClient.patch<VendorProduct>(endpoints.vendorProducts.details(id), payload);
    return response.data;
  },
};
