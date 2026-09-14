import { cn } from "@/lib/utils/cn";
import type { VerificationStatus } from "@/types/kyc";

const STEPS: VerificationStatus[] = ["pending", "under_review", "verified"];
const STEP_LABELS: Record<VerificationStatus, string> = {
  pending: "Submitted",
  under_review: "Under review",
  verified: "Verified",
  rejected: "Rejected",
  expired: "Expired",
};

export function VerificationProgress({ status }: { status: VerificationStatus }) {
  if (status === "rejected" || status === "expired") {
    return <p className="text-sm text-thread">{STEP_LABELS[status]} — please resubmit your documents.</p>;
  }

  const currentIndex = STEPS.indexOf(status);

  return (
    <div className="flex items-center gap-2">
      {STEPS.map((step, i) => (
        <div key={step} className="flex items-center gap-2">
          <div
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full text-xs",
              i <= currentIndex ? "bg-brass text-ink" : "bg-muslin text-ink-soft"
            )}
          >
            {i + 1}
          </div>
          <span className={cn("text-xs", i <= currentIndex ? "text-ink" : "text-ink-soft")}>{STEP_LABELS[step]}</span>
          {i < STEPS.length - 1 && <div className="h-px w-6 bg-line" />}
        </div>
      ))}
    </div>
  );
}
