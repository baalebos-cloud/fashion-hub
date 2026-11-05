import { apiClient } from "@/lib/api/client";
import type { VerificationQueueItem, VerificationSummary } from "@/types/verification";

export const verificationApi = {
  async me(): Promise<VerificationSummary> {
    return (await apiClient.get<VerificationSummary>("/verification/me")).data;
  },
  async queue(kind: "kyc" | "kyb"): Promise<VerificationQueueItem[]> {
    return (await apiClient.get<VerificationQueueItem[]>("/admin/verifications", { params: { kind } })).data;
  },
  async review(kind: "kyc" | "kyb", id: string, approve: boolean, reason?: string): Promise<{ id: string; status: string }> {
    return (await apiClient.post<{ id: string; status: string }>(`/admin/${kind}/${id}/review`,
      { approve, reason: reason?.trim() || null })).data;
  },
  /** Private document: fetched with the admin's session, opened as a short-lived blob URL. */
  async openDocument(documentId: string): Promise<void> {
    const response = await apiClient.get<Blob>(`/admin/verification-documents/${documentId}/content`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  },
};
