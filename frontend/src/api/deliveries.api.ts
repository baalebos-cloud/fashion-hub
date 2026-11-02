import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery, DeliveryTrip } from "@/types/delivery";

export const deliveriesApi = {
  async markPickedUp(id: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveries.pickedUp(id));
    return response.data;
  },
  async markDelivered(id: string, handoverCode: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveries.delivered(id), { handover_code: handoverCode });
    return response.data;
  },
  async getTrip(id: string): Promise<DeliveryTrip> {
    return (await apiClient.get<DeliveryTrip>(endpoints.deliveries.trip(id))).data;
  },
  async getHandoverCode(id: string): Promise<string> {
    const response = await apiClient.get<{ handover_code: string }>(endpoints.deliveries.handoverCode(id));
    return response.data.handover_code;
  },
  async getByOrder(orderId: string): Promise<Delivery | null> {
    const response = await apiClient.get<Delivery | null>(endpoints.deliveries.byOrder(orderId));
    return response.data;
  },
  async getById(id: string): Promise<Delivery> {
    const response = await apiClient.get<Delivery>(endpoints.deliveries.details(id));
    return response.data;
  },
};
