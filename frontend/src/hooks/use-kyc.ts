import { useEffect, useState } from "react";
import { kycApi } from "@/api/kyc.api";
import type { KYCStatus } from "@/types/kyc";

export function useKYC() {
  const [status, setStatus] = useState<KYCStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    kycApi
      .getStatus()
      .then(setStatus)
      .finally(() => setIsLoading(false));
  }, []);

  async function submit(idType: string, documentStorageKeys: string[]) {
    const result = await kycApi.submit(idType, documentStorageKeys);
    setStatus(result);
    return result;
  }

  return { status, isLoading, submit };
}
