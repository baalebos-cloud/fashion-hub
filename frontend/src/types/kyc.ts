export type VerificationStatus = "pending" | "under_review" | "verified" | "rejected" | "expired";

export interface KYCStatus {
  status: VerificationStatus;
  id_type?: string | null;
  // Populated FROM the NIN lookup, not from what the person typed --
  // see backend/docs/nin-verification.md. Shown back to the person as
  // read-only confirmation of what the government record says, distinct
  // from their own account full_name.
  nin_verified_full_name?: string | null;
  nin_verified_date_of_birth?: string | null;
  nin_verified_gender?: string | null;
  identity_match?: boolean | null;
  rejection_reason?: string | null;
}

export interface SubmitKYCPayload {
  nin_number: string;
  document_storage_keys: string[];
  home_latitude: number;
  home_longitude: number;
  home_formatted_address?: string;
}
