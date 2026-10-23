import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery } from "@/types/delivery";

export const deliveriesApi = {
  async markPickedUp(id: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveries.pickedUp(id));
    return response.data;
  },
  async markDelivered(id: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveries.delivered(id));
    return response.data;
  },
  async getById(id: string): Promise<Delivery> {
    const response = await apiClient.get<Delivery>(endpoints.deliveries.details(id));
    return response.data;
  },
};
