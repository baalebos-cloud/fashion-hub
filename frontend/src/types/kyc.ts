export type VerificationStatus = "pending" | "under_review" | "verified" | "rejected" | "expired";

export interface KYCStatus {
  status: VerificationStatus;
  rejection_reason?: string | null;
}
