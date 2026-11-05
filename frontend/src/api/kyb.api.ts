import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { CompanyType, KYBStatus } from "@/types/kyb";

export const kybApi = {
  async submit(registrationNumber: string, companyType: CompanyType, documentStorageKeys: string[]): Promise<KYBStatus> {
    const response = await apiClient.post<KYBStatus>(endpoints.kyb.submit, {
      business_registration_number: registrationNumber,
      company_type: companyType,
      document_storage_keys: documentStorageKeys,
    });
    return response.data;
  },

  async getStatus(): Promise<KYBStatus> {
    const response = await apiClient.get<KYBStatus>(endpoints.kyb.status);
    return response.data;
  },
};
