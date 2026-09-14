import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { DashboardSummaryCard } from "@/types/dashboard";

export const dashboardApi = {
  async getSummary(): Promise<DashboardSummaryCard[]> {
    const response = await apiClient.get<DashboardSummaryCard[]>(endpoints.dashboard.summary);
    return response.data;
  },
};
