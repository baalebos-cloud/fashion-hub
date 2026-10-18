import { useState } from "react";
import { checkoutApi, type MaterialCheckout } from "@/api/checkout.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export function useCheckout() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(payload: MaterialCheckout) {
    setIsSubmitting(true);
    setError(null);
    try {
      return await checkoutApi.submit(payload);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Checkout failed. Please try again."));
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }
  return { submit, isSubmitting, error };
}
