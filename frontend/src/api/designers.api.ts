import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Designer } from "@/types/designer";

export const designersApi = {
  async getById(id: string): Promise<Designer> {
    const response = await apiClient.get<Designer>(endpoints.designers.details(id));
    return response.data;
  },
};
