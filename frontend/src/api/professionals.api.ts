import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Professional } from "@/types/professional";
import type { PaginatedResponse, PaginationParams } from "@/types/api";

export interface ProfessionalSearchParams extends PaginationParams {
  professionalType?: "tailor" | "designer";
  latitude?: number;
  longitude?: number;
  radiusKm?: number;
  query?: string;
}

export const professionalsApi = {
  async list(params: ProfessionalSearchParams = {}): Promise<PaginatedResponse<Professional>> {
    const response = await apiClient.get<PaginatedResponse<Professional>>(endpoints.professionals.list, {
      params: {
        professional_type: params.professionalType,
        lat: params.latitude,
        lng: params.longitude,
        radius_km: params.radiusKm,
        q: params.query,
        page: params.page,
        page_size: params.pageSize,
      },
    });
    return response.data;
  },

  async getById(id: string): Promise<Professional> {
    const response = await apiClient.get<Professional>(endpoints.professionals.details(id));
    return response.data;
  },
};
