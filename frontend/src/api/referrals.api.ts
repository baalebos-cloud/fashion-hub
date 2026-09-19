import { apiClient } from "@/lib/api/client";
import type { Referral, ReferralCode, ReferralSummary } from "@/types/referral";

export const referralsApi = {
  async getMyCode(): Promise<ReferralCode> {
    const response = await apiClient.get<ReferralCode>("/referrals/code");
    return response.data;
  },

  async getMySummary(): Promise<ReferralSummary> {
    const response = await apiClient.get<ReferralSummary>("/referrals/me");
    return response.data;
  },

  async markPaid(referralId: string): Promise<Referral> {
    const response = await apiClient.post<Referral>(`/referrals/${referralId}/mark-paid`);
    return response.data;
  },
};
