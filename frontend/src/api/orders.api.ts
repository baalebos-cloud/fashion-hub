import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { CreateCustomerOrderPayload, Order, OrderTimelineEntry } from "@/types/order";
import type { OrderTrackingResponse } from "@/types/tracking";

/**
 * Mirrors the exact required backend endpoint surface
 * (backend/docs/orders.md) one-to-one. Every mutating call here changes
 * nothing on its own — the backend independently re-validates the state
 * transition and ownership on every request (see
 * backend/app/services/order_service.py). This file exists purely to
 * avoid scattering these path strings across components.
 */
export const ordersApi = {
  async list(): Promise<Order[]> {
    const response = await apiClient.get<Order[]>(endpoints.orders.list);
    return response.data;
  },

  async getById(id: string): Promise<Order> {
    const response = await apiClient.get<Order>(endpoints.orders.details(id));
    return response.data;
  },

  async create(payload: CreateCustomerOrderPayload): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.list, payload);
    return response.data;
  },

  async accept(id: string, note?: string): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.accept(id), { note });
    return response.data;
  },

  async startProduction(id: string, note?: string): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.startProduction(id), { note });
    return response.data;
  },

  async markReady(id: string, note?: string): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.ready(id), { note });
    return response.data;
  },

  async ship(id: string, note?: string): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.ship(id), { note });
    return response.data;
  },

  async getTracking(id: string): Promise<OrderTrackingResponse> {
    const response = await apiClient.get<OrderTrackingResponse>(endpoints.orders.tracking(id));
    return response.data;
  },

  /** Only ever succeeds when called by the order's own customer — the
   * backend enforces this regardless of who the frontend lets click the
   * button (see backend/docs/orders.md#mark-as-received-rule). */
  async markReceived(id: string, note?: string): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.received(id), { note });
    return response.data;
  },

  async getTimeline(id: string): Promise<OrderTimelineEntry[]> {
    const response = await apiClient.get<OrderTimelineEntry[]>(endpoints.orders.timeline(id));
    return response.data;
  },

  async submitReview(id: string, score: number, comment?: string): Promise<void> {
    await apiClient.post(endpoints.orders.review(id), { score, comment });
  },

  async cancel(id: string, note?: string): Promise<Order> {
    const response = await apiClient.post<Order>(endpoints.orders.cancel(id), { note });
    return response.data;
  },
};
