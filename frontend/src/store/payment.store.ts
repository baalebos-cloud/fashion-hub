import { create } from "zustand";
import { paymentsApi } from "@/api/payments.api";
import type { Payment } from "@/types/payment";

interface PaymentState {
  isInitializing: boolean;
  error: string | null;
  startPayment: (orderId: string, callbackUrl: string) => Promise<string>;
  verifyPayment: (providerReference: string) => Promise<Payment>;
}

export const usePaymentStore = create<PaymentState>((set) => ({
  isInitializing: false,
  error: null,

  startPayment: async (orderId, callbackUrl) => {
    set({ isInitializing: true, error: null });
    try {
      const result = await paymentsApi.initialize(orderId, callbackUrl);
      return result.authorization_url;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not start payment." });
      throw err;
    } finally {
      set({ isInitializing: false });
    }
  },

  verifyPayment: async (providerReference) => paymentsApi.verify(providerReference),
}));
