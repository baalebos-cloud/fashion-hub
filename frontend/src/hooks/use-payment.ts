import { usePaymentStore } from "@/store/payment.store";
import { redirectToPaymentProvider } from "@/lib/payments/payment-client";

export function usePayment() {
  const { isInitializing, error, startPayment, verifyPayment } = usePaymentStore();

  async function payAndRedirect(orderId: string, callbackUrl: string) {
    const authorizationUrl = await startPayment(orderId, callbackUrl);
    redirectToPaymentProvider(authorizationUrl);
  }

  return { payAndRedirect, verifyPayment, isInitializing, error };
}
