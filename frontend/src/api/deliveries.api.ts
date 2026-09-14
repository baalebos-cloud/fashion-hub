import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery } from "@/types/delivery";

export const deliveriesApi = {
  async getById(id: string): Promise<Delivery> {
    const response = await apiClient.get<Delivery>(endpoints.deliveries.details(id));
    return response.data;
  },
};
