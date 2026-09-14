import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Customer } from "@/types/customer";

export const customersApi = {
  async getMe(): Promise<Customer> {
    const response = await apiClient.get<Customer>(endpoints.customers.me);
    return response.data;
  },
};
