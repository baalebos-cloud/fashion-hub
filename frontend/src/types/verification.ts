export type StepStatus = "not_started" | "pending" | "under_review" | "verified" | "rejected" | "expired";

export interface VerificationStep {
  key: "identity" | "business";
  title: string;
  required: boolean;
  status: StepStatus;
  rejection_reason: string | null;
  submitted_at: string | null;
  action: "kyc" | "kyb";
}

export interface VerificationSummary {
  role: string;
  verified: boolean;
  steps: VerificationStep[];
  next_step: string | null;
}

export interface VerificationQueueItem {
  id: string;
  status: "pending" | "under_review";
  submitted_at: string;
  applicant_name: string;
  applicant_role: string;
  documents: { id: string; type: string }[];
  /** Name from the official registry (NIN or CAC); null when the registry couldn't be reached. */
  official_name: string | null;
  name_match: boolean | null;
  registry_checked: boolean;
  /** Identity checks only: which automatic-approval rules passed (true) or failed (false). */
  auto_checks?: Record<string, boolean> | null;
  business_name?: string | null;
  registration?: string;
}
