import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Invoice } from "@/types/invoice";

export const invoicesApi = {
  async getById(id: string): Promise<Invoice> {
    const response = await apiClient.get<Invoice>(endpoints.invoices.details(id));
    return response.data;
  },

  async getByOrderId(orderId: string): Promise<Invoice> {
    const response = await apiClient.get<Invoice>(endpoints.invoices.byOrder(orderId));
    return response.data;
  },
};
