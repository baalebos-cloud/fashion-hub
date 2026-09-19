import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { CreateDesignPayload, Design } from "@/types/design";

/**
 * GET /designs returns a plain array (see backend/app/api/v1/designs.py --
 * there's no pagination on this endpoint yet since it's always scoped to
 * one professional's design list, which is small in practice).
 */
export const designsApi = {
  async list(params: { professionalId?: string } = {}): Promise<Design[]> {
    if (!params.professionalId) return [];
    const response = await apiClient.get<Design[]>(endpoints.designs.list, {
      params: { professional_id: params.professionalId },
    });
    return response.data;
  },

  async create(payload: CreateDesignPayload): Promise<Design> {
    const response = await apiClient.post<Design>(endpoints.designs.list, payload);
    return response.data;
  },
};
