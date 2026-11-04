import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery, DeliveryTrip, RiderPosition } from "@/types/delivery";

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
  async publishPosition(id: string, payload: Pick<RiderPosition, "latitude" | "longitude" | "accuracy_m">): Promise<RiderPosition> {
    return (await apiClient.post<RiderPosition>(endpoints.deliveries.position(id), payload)).data;
  },
  async getPosition(id: string): Promise<RiderPosition | null> {
    return (await apiClient.get<RiderPosition | null>(endpoints.deliveries.position(id))).data;
  },
  async stopPosition(id: string): Promise<void> {
    await apiClient.delete(endpoints.deliveries.position(id));
  },
  async getById(id: string): Promise<Delivery> {
    const response = await apiClient.get<Delivery>(endpoints.deliveries.details(id));
    return response.data;
  },
};
