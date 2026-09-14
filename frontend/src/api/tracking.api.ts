import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { OrderTrackingResponse } from "@/types/tracking";

export const trackingApi = {
  async getForOrder(orderId: string): Promise<OrderTrackingResponse> {
    const response = await apiClient.get<OrderTrackingResponse>(endpoints.tracking.byOrder(orderId));
    return response.data;
  },
};
