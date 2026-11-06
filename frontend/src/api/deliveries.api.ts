import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery, DeliveryTrip, HandoverCode, PickupCode, RiderPosition } from "@/types/delivery";

/** One key per user action, so a retry after a dropped connection is applied only once. */
export function newIdempotencyKey(): string {
  const random = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `web-${random}`;
}

export const deliveriesApi = {
  async markPickedUp(id: string, body: { pickup_code?: string; package_count: number }, idempotencyKey?: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveries.pickedUp(id), body,
      idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined);
    return response.data;
  },
  async markDelivered(id: string, handoverCode: string, idempotencyKey?: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveries.delivered(id), { handover_code: handoverCode },
      idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined);
    return response.data;
  },
  async getTrip(id: string): Promise<DeliveryTrip> {
    return (await apiClient.get<DeliveryTrip>(endpoints.deliveries.trip(id))).data;
  },
  /** Buyer only, after pickup. Codes expire; a lapsed one is replaced automatically. */
  async getHandoverCode(id: string): Promise<HandoverCode> {
    return (await apiClient.get<HandoverCode>(endpoints.deliveries.handoverCode(id))).data;
  },
  async rotateHandoverCode(id: string): Promise<HandoverCode> {
    return (await apiClient.post<HandoverCode>(`${endpoints.deliveries.handoverCode(id)}/rotate`)).data;
  },
  /** Seller only, while the rider is coming to collect. */
  async getPickupCode(id: string): Promise<PickupCode> {
    return (await apiClient.get<PickupCode>(endpoints.deliveries.pickupCode(id))).data;
  },
  async rotatePickupCode(id: string): Promise<PickupCode> {
    return (await apiClient.post<PickupCode>(`${endpoints.deliveries.pickupCode(id)}/rotate`)).data;
  },
  async getByOrder(orderId: string): Promise<Delivery | null> {
    const response = await apiClient.get<Delivery | null>(endpoints.deliveries.byOrder(orderId));
    return response.data;
  },
  async startPosition(id: string): Promise<string> {
    return (await apiClient.post<{ share_token: string }>(endpoints.deliveries.positionStart(id))).data.share_token;
  },
  async publishPosition(id: string, payload: Pick<RiderPosition, "latitude" | "longitude" | "accuracy_m"> & { share_token: string; recorded_at?: string; speed_mps?: number }): Promise<RiderPosition> {
    return (await apiClient.post<RiderPosition>(endpoints.deliveries.position(id), payload)).data;
  },
  /** The phone reports why there's no location: permission off, no GPS, or page in background. */
  async reportPositionState(id: string, shareToken: string, state: "permission_denied" | "unavailable" | "paused"): Promise<void> {
    await apiClient.post(`${endpoints.deliveries.position(id)}/state`, { share_token: shareToken, state });
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
