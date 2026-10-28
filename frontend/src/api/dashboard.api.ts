import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { DashboardSummaryCard } from "@/types/dashboard";

export type CommerceSummary = {
  currency: "NGN";
  verified_count: number;
  verified_volume_ngn: string;
  by_provider: Array<{ provider: string; status: string; count: number; amount_ngn: string }>;
  note: string;
};

export const dashboardApi = {
  async getCommerceSummary(): Promise<CommerceSummary> {
    const response = await apiClient.get<CommerceSummary>(endpoints.adminCommerce.summary);
    return response.data;
  },
  async getSummary(): Promise<DashboardSummaryCard[]> {
    const response = await apiClient.get<DashboardSummaryCard[]>(endpoints.dashboard.summary);
    return response.data;
  },
};
