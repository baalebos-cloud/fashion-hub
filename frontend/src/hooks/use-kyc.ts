import { useEffect, useState } from "react";
import { kycApi } from "@/api/kyc.api";
import type { KYCStatus, SubmitKYCPayload } from "@/types/kyc";

export function useKYC() {
  const [status, setStatus] = useState<KYCStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    kycApi
      .getStatus()
      .then(setStatus)
      .catch(() => setStatus(null)) // "no submission yet" surfaces as a 404 -- not an error state to show
      .finally(() => setIsLoading(false));
  }, []);

  async function submit(payload: SubmitKYCPayload) {
    const result = await kycApi.submit(payload);
    setStatus(result);
    return result;
  }

  return { status, isLoading, submit };
}
