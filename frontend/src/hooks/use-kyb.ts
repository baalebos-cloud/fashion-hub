import { useEffect, useState } from "react";
import { kybApi } from "@/api/kyb.api";
import type { CompanyType, KYBStatus } from "@/types/kyb";

export function useKYB() {
  const [status, setStatus] = useState<KYBStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    kybApi
      .getStatus()
      .then(setStatus)
      .catch(() => setStatus(null)) // "no submission yet" is a 404, not an error to show
      .finally(() => setIsLoading(false));
  }, []);

  async function submit(registrationNumber: string, companyType: CompanyType, documentStorageKeys: string[]) {
    const result = await kybApi.submit(registrationNumber, companyType, documentStorageKeys);
    setStatus(result);
    return result;
  }

  return { status, isLoading, submit };
}
