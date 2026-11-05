import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Delivery } from "@/types/delivery";
import type { DeliveryJourney, DispatchJob, MyOffer, SellerDispatchView } from "@/types/dispatch";

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
  /** Priced job cards for verified, available riders. */
  async available(): Promise<DispatchJob[]> {
    const response = await apiClient.get<DispatchJob[]>(endpoints.deliveryRequests.available);
    return response.data;
  },
  /** Instant claim at the suggested fare. */
  async accept(requestId: string): Promise<Delivery> {
    const response = await apiClient.post<Delivery>(endpoints.deliveryRequests.accept(requestId));
    return response.data;
  },
  async makeOffer(requestId: string, amount: number, etaToPickupMinutes: number): Promise<MyOffer> {
    const response = await apiClient.post<MyOffer>(`/delivery-requests/${requestId}/offers`,
      { amount, eta_to_pickup_minutes: etaToPickupMinutes });
    return response.data;
  },
  async withdrawOffer(requestId: string): Promise<void> {
    await apiClient.delete(`/delivery-requests/${requestId}/offers/mine`);
  },
  async sellerDispatch(orderId: string): Promise<SellerDispatchView> {
    return (await apiClient.get<SellerDispatchView>(`/delivery-requests/orders/${orderId}/dispatch`)).data;
  },
  async acceptOffer(offerId: string): Promise<Delivery> {
    return (await apiClient.post<Delivery>(`/delivery-requests/offers/${offerId}/accept`)).data;
  },
  async journey(orderId: string): Promise<DeliveryJourney> {
    return (await apiClient.get<DeliveryJourney>(`/deliveries/orders/${orderId}/journey`)).data;
  },
};
