import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { KYCStatus, SubmitKYCPayload } from "@/types/kyc";

export const kycApi = {
  async submit(payload: SubmitKYCPayload): Promise<KYCStatus> {
    // Tailora checks everything during submission: NIN (≤15 s), then the document (≤40 s), then both
    // face checks at once (≤20 s), about 75 s at worst, so allow up to 90 s.
    const response = await apiClient.post<KYCStatus>(endpoints.kyc.submit, payload, { timeout: 90_000 });
    return response.data;
  },

  async getStatus(): Promise<KYCStatus> {
    const response = await apiClient.get<KYCStatus>(endpoints.kyc.status);
    return response.data;
  },
};
