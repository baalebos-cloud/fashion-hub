import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export interface AdminOperations {
  marketplace: Record<string, number>;
  verification: {
    kyc_pending: Array<{ id: string; user_id: string; status?: string; documents: string[] }>;
    kyb_pending: Array<{ id: string; owner_id: string; status?: string; documents: string[] }>;
  };
  financial_controls: { production_payments_enabled: boolean; ledger_balanced: boolean; ledger_debits_minor?: number; ledger_credits_minor?: number };
  delivery_issues: Array<{ id: string; delivery_id?: string; type: string; status: string }>;
  audit_events: Array<{ id: string; action: string; actor_id?: string | null }>;
}

/** Admin overview counts. No raw NIN or document contents are returned here. */
export const adminOperationsApi = {
  async operations(): Promise<AdminOperations> {
    return (await apiClient.get<AdminOperations>(endpoints.admin.operations)).data;
  },
};
