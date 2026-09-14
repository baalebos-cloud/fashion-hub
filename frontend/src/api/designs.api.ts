import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Design } from "@/types/design";
import type { PaginatedResponse, PaginationParams } from "@/types/api";

export const designsApi = {
  async list(params: PaginationParams & { professionalId?: string } = {}): Promise<PaginatedResponse<Design>> {
    const response = await apiClient.get<PaginatedResponse<Design>>(endpoints.designs.list, {
      params: { professional_id: params.professionalId, page: params.page, page_size: params.pageSize },
    });
    return response.data;
  },

  async getById(id: string): Promise<Design> {
    const response = await apiClient.get<Design>(endpoints.designs.details(id));
    return response.data;
  },
};
