import { apiClient } from "@/lib/api/client";
import { stepUpHeaders } from "@/api/verification.api";

export interface PayoutAccount {
  bank_name: string;
  account_last4: string;
  account_name: string;
  name_matches: boolean;
  verified_at: string;
}

export interface SellerPayout {
  order_id: string;
  gross_amount: number;
  commission_amount: number;
  net_amount: number;
  currency: string;
  status: "pending" | "processing" | "paid" | "failed" | "held";
  hold_reason: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface AdminPayout {
  id: string;
  status: SellerPayout["status"];
  order_number: string;
  order_status: string;
  seller_name: string;
  net_amount: number;
  currency: string;
  hold_reason: string | null;
  failure_reason: string | null;
  attempts: number;
  paid_at: string | null;
  created_at: string;
}

export const payoutsApi = {
  async banks(): Promise<{ code: string; name: string }[]> {
    return (await apiClient.get("/payments/payout-account/banks")).data;
  },
  async account(): Promise<{ account: PayoutAccount | null; payouts_enabled: boolean }> {
    return (await apiClient.get("/payments/payout-account")).data;
  },
  /** Needs the seller's password, so a stolen session can't redirect their money. */
  async setAccount(body: { bank_code: string; account_number: string; password: string }): Promise<PayoutAccount> {
    return (await apiClient.put("/payments/payout-account", body, { timeout: 45_000 })).data;
  },
  async mine(): Promise<SellerPayout[]> {
    return (await apiClient.get("/payments/payouts", { params: { page_size: 50 } })).data;
  },
  async adminList(status?: string): Promise<{ payouts_enabled: boolean; items: AdminPayout[] }> {
    return (await apiClient.get("/admin/payouts", { params: status ? { status } : undefined })).data;
  },
  async adminHold(id: string, reason: string): Promise<void> {
    await apiClient.post(`/admin/payouts/${id}/hold`, { reason });
  },
  /** Needs an open review window (fresh authenticator code). */
  async adminRelease(id: string): Promise<void> {
    await apiClient.post(`/admin/payouts/${id}/release`, null, { headers: stepUpHeaders() });
  },
};
