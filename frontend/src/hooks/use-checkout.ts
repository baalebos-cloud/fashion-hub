import { useState } from "react";
import { checkoutApi } from "@/api/checkout.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Order } from "@/types/order";

export function useCheckout() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(cartId: string, deliveryAddressId: string): Promise<Order[]> {
    setIsSubmitting(true);
    setError(null);
    try {
      return await checkoutApi.submit(cartId, deliveryAddressId);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Checkout failed. Please try again."));
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }

  return { submit, isSubmitting, error };
}
