import { apiClient } from "@/lib/api/client";
import { stepUpHeaders } from "@/api/verification.api";

export type DisputeReason = "not_delivered" | "wrong_item" | "wrong_size" | "damaged" | "poor_quality" | "other";
export type DisputeOutcome = "refund" | "remake" | "no_action";

export const DISPUTE_REASONS: { value: DisputeReason; label: string }[] = [
  { value: "not_delivered", label: "It wasn't delivered" },
  { value: "wrong_size", label: "Wrong size or fit" },
  { value: "wrong_item", label: "Wrong item or design" },
  { value: "damaged", label: "It arrived damaged" },
  { value: "poor_quality", label: "Poor quality or finishing" },
  { value: "other", label: "Something else" },
];

export interface Dispute {
  id: string;
  order_id: string;
  /** "resolving": an admin is part-way through a refund; still counts as open. */
  status: "open" | "resolving" | "resolved";
  reason: DisputeReason;
  reason_label: string;
  description: string;
  outcome: DisputeOutcome | null;
  outcome_label: string | null;
  resolution_note: string | null;
  refund_amount: number | null;
  created_at: string | null;
  resolved_at: string | null;
  // Admin list only:
  order_number?: string;
  order_type?: string;
  order_total?: number;
  currency?: string;
  buyer_name?: string | null;
  seller_name?: string | null;
}

export const disputesApi = {
  async open(orderId: string, reason: DisputeReason, description: string): Promise<Dispute> {
    return (await apiClient.post<Dispute>("/disputes", { order_id: orderId, reason, description })).data;
  },
  async forOrder(orderId: string): Promise<Dispute[]> {
    return (await apiClient.get<Dispute[]>("/disputes/mine", { params: { order_id: orderId } })).data;
  },
  async adminList(params: Record<string, string | number | undefined>) {
    return (await apiClient.get<{ total: number; page: number; page_size: number; items: Dispute[] }>("/admin/disputes", { params })).data;
  },
  /** A refund needs an open authenticator-code window (stepUpHeaders). */
  async resolve(id: string, body: { outcome: DisputeOutcome; note: string; refund_amount?: string }): Promise<Dispute> {
    return (await apiClient.post<Dispute>(`/admin/disputes/${id}/resolve`, body,
      { headers: body.outcome === "refund" ? stepUpHeaders() : undefined })).data;
  },
};
