import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { InitializePaymentResponse, Payment } from "@/types/payment";
import type { InterswitchCheckout } from "@/lib/interswitchCheckout";

export const paymentsApi = {
  /** User-initiated and disabled by default at backend + frontend gates. */
  async initializeInterswitch(orderId: string): Promise<InterswitchCheckout> {
    const response = await apiClient.post<InterswitchCheckout>(
      endpoints.interswitch.initialize, { order_id: orderId },
    );
    return response.data;
  },
  async initializeLiveInterswitch(orderId: string): Promise<InterswitchCheckout> {
    const response = await apiClient.post<InterswitchCheckout>(
      endpoints.interswitch.initializeLive, { order_id: orderId },
    );
    return response.data;
  },
  async verifyLiveInterswitch(reference: string): Promise<Payment> {
    const response = await apiClient.get<Payment>(endpoints.interswitch.verifyLive(reference));
    return response.data;
  },
  async verifyInterswitch(reference: string): Promise<Payment> {
    const response = await apiClient.get<Payment>(
      endpoints.interswitch.verify(reference),
    );
    return response.data;
  },

  async initialize(orderId: string, callbackUrl: string): Promise<InitializePaymentResponse> {
    const response = await apiClient.post<InitializePaymentResponse>(endpoints.payments.initialize, {
      order_id: orderId,
      callback_url: callbackUrl,
    });
    return response.data;
  },

  /** Belt-and-suspenders client-triggered verification on the payment
   * callback page — the backend independently confirms with the provider
   * server-to-server rather than trusting this call's mere occurrence. */
  async verify(providerReference: string): Promise<Payment> {
    const response = await apiClient.get<Payment>(endpoints.payments.verify(providerReference));
    return response.data;
  },
};
