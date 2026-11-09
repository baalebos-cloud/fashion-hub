import { apiClient } from "@/lib/api/client";
import type { VerificationQueueItem, VerificationSummary } from "@/types/verification";

/** A short review window opened by a fresh authenticator code. Kept in memory only:
 * a reload or another tab asks for a code again. */
let reviewPass: { token: string; expiresAt: number } | null = null;

export function hasReviewWindow(now = Date.now()): boolean {
  return reviewPass !== null && reviewPass.expiresAt - 15_000 > now;
}

export function endReviewWindow(): void {
  reviewPass = null;
}

export const verificationApi = {
  async me(): Promise<VerificationSummary> {
    return (await apiClient.get<VerificationSummary>("/verification/me")).data;
  },
  async queue(kind: "kyc" | "kyb"): Promise<VerificationQueueItem[]> {
    return (await apiClient.get<VerificationQueueItem[]>("/admin/verifications", { params: { kind } })).data;
  },
  /** Exchange a fresh authenticator code for a short review window. */
  async openReviewWindow(code: string): Promise<void> {
    const { data } = await apiClient.post<{ step_up_token: string; minutes: number }>("/admin/step-up", { code });
    reviewPass = { token: data.step_up_token, expiresAt: Date.now() + data.minutes * 60_000 };
  },
  /** Needs an open review window; the backend refuses with code "step_up_required" otherwise. */
  async review(kind: "kyc" | "kyb", id: string, approve: boolean, reason?: string): Promise<{ id: string; status: string }> {
    const headers = reviewPass ? { "X-Admin-Step-Up": reviewPass.token } : undefined;
    return (await apiClient.post<{ id: string; status: string }>(`/admin/${kind}/${id}/review`,
      { approve, reason: reason?.trim() || null }, { headers })).data;
  },
  /** Private document fetched with the admin's session, as a blob URL the caller shows in-page
   * (opening a new window doesn't work inside the phone apps) and revokes when closed. */
  async loadDocument(documentId: string): Promise<{ url: string; type: string }> {
    const response = await apiClient.get<Blob>(`/admin/verification-documents/${documentId}/content`, { responseType: "blob" });
    return { url: URL.createObjectURL(response.data), type: response.data.type || "application/octet-stream" };
  },
  /** Run Tailora's document check on a waiting identity submission (adds a note; never decides). */
  async checkDocument(id: string): Promise<{ checks: Record<string, boolean>; document_note: string; passed: boolean }> {
    return (await apiClient.post(`/admin/kyc/${id}/document-check`, null, { timeout: 60_000 })).data;
  },
};
