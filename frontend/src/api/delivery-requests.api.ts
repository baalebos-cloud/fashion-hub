import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery } from "@/types/delivery";

export interface InternalDeliveryRequest {
  id: string;
  order_id: string;
  status: string;
}

export const deliveryRequestsApi = {
  async requestForOrder(orderId: string): Promise<InternalDeliveryRequest> {
    const response = await apiClient.post<InternalDeliveryRequest>(endpoints.deliveryRequests.forOrder(orderId));
    return response.data;
  },
  async available(): Promise<InternalDeliveryRequest[]> {
    const response = await apiClient.get<InternalDeliveryRequest[]>(endpoints.deliveryRequests.available);
    return response.data;
  },
  async accept(requestId: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveryRequests.accept(requestId));
    return response.data;
  },
};
