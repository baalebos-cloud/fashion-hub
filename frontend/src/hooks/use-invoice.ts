import { useEffect, useState } from "react";
import { invoicesApi } from "@/api/invoices.api";
import type { Invoice } from "@/types/invoice";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export function useInvoice(orderId: string | undefined) {
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) return;
    setIsLoading(true);
    invoicesApi
      .getByOrderId(orderId)
      .then(setInvoice)
      .catch((err) => setError(getDisplayErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, [orderId]);

  return { invoice, isLoading, error };
}
