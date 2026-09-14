import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export interface Category {
  id: string;
  name: string;
  slug: string;
}

export const categoriesApi = {
  async list(): Promise<Category[]> {
    const response = await apiClient.get<Category[]>(endpoints.categories.list);
    return response.data;
  },
};
