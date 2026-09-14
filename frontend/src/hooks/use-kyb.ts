import { useEffect, useState } from "react";
import { kybApi } from "@/api/kyb.api";
import type { KYBStatus } from "@/types/kyb";

export function useKYB() {
  const [status, setStatus] = useState<KYBStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    kybApi
      .getStatus()
      .then(setStatus)
      .finally(() => setIsLoading(false));
  }, []);

  async function submit(registrationNumber: string, documentStorageKeys: string[]) {
    const result = await kybApi.submit(registrationNumber, documentStorageKeys);
    setStatus(result);
    return result;
  }

  return { status, isLoading, submit };
}
