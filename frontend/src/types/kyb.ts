import type { VerificationStatus } from "./kyc";

export interface KYBStatus {
  status: VerificationStatus;
  rejection_reason?: string | null;
}
