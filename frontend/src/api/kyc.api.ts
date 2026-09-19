import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { KYCStatus, SubmitKYCPayload } from "@/types/kyc";

export const kycApi = {
  async submit(payload: SubmitKYCPayload): Promise<KYCStatus> {
    const response = await apiClient.post<KYCStatus>(endpoints.kyc.submit, payload);
    return response.data;
  },

  async getStatus(): Promise<KYCStatus> {
    const response = await apiClient.get<KYCStatus>(endpoints.kyc.status);
    return response.data;
  },
};
