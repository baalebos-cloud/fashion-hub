import { VerificationProgress } from "./VerificationProgress";
import type { VerificationStatus as VerificationStatusType } from "@/types/kyc";

export function VerificationStatus({ status }: { status: VerificationStatusType | null }) {
  if (!status) {
    return <p className="text-sm text-ink-soft">You haven't submitted verification documents yet.</p>;
  }
  return <VerificationProgress status={status} />;
}
