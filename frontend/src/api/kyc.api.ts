import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { KYCStatus } from "@/types/kyc";

export const kycApi = {
  async submit(idType: string, documentStorageKeys: string[]): Promise<KYCStatus> {
    const response = await apiClient.post<KYCStatus>(endpoints.kyc.submit, {
      id_type: idType,
      document_storage_keys: documentStorageKeys,
    });
    return response.data;
  },

  async getStatus(): Promise<KYCStatus> {
    const response = await apiClient.get<KYCStatus>(endpoints.kyc.status);
    return response.data;
  },
};
