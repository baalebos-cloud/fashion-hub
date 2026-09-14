import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { InitializePaymentResponse } from "@/types/payment";

/**
 * The frontend's entire role in payments: ask the backend to start a
 * payment session, then redirect the browser to the provider's hosted
 * checkout page. It never talks to Paystack/Flutterwave directly, never
 * decides a payment succeeded on its own, and never sees a secret key —
 * see backend/docs/payments.md for the full "never trust the client" rule
 * this mirrors.
 */
export async function initializePayment(orderId: string, callbackUrl: string): Promise<InitializePaymentResponse> {
  const response = await apiClient.post<InitializePaymentResponse>(endpoints.payments.initialize, {
    order_id: orderId,
    callback_url: callbackUrl,
  });
  return response.data;
}

export function redirectToPaymentProvider(authorizationUrl: string): void {
  window.location.assign(authorizationUrl);
}
