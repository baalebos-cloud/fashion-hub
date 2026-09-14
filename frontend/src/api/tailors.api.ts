import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Tailor } from "@/types/tailor";

export const tailorsApi = {
  async getById(id: string): Promise<Tailor> {
    const response = await apiClient.get<Tailor>(endpoints.tailors.details(id));
    return response.data;
  },
};
