import type { VerificationStatus } from "./kyc";

export type CompanyType = "RC" | "BN" | "IT";

export interface KYBStatus {
  status: VerificationStatus;
  company_type?: CompanyType | null;
  business_registration_number?: string | null;
  /** From the CAC registry lookup, never from what the person typed. */
  verified_company_name?: string | null;
  name_match?: boolean | null;
  rejection_reason?: string | null;
}
