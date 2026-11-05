import { useEffect, useState } from "react";
import { verificationApi } from "@/api/verification.api";
import { Card } from "@/components/ui/card";
import { VerifiedBadge } from "./VerifiedBadge";
import { KYCForm } from "./KYCForm";
import { KYBForm } from "./KYBForm";
import type { StepStatus, VerificationStep, VerificationSummary } from "@/types/verification";

const STATUS_CHIP: Record<StepStatus, { label: string; className: string }> = {
  not_started: { label: "Not started", className: "bg-muslin text-ink-soft" },
  pending: { label: "In review", className: "bg-[#e6ecff] text-[#2c3e9e]" },
  under_review: { label: "In review", className: "bg-[#e6ecff] text-[#2c3e9e]" },
  verified: { label: "Verified", className: "bg-[#e5f3ea] text-[#256a3f]" },
  rejected: { label: "Needs attention", className: "bg-[#fbecea] text-thread" },
  expired: { label: "Expired", className: "bg-[#fbf0dd] text-[#8a5f1f]" },
};

const WHY: Record<string, string> = {
  identity: "Confirms you are who you say you are, using your NIN.",
  business: "Confirms your business is registered with the CAC.",
};

function Step({ step, index, onChanged }: { step: VerificationStep; index: number; onChanged: () => void }) {
  const chip = STATUS_CHIP[step.status] ?? STATUS_CHIP.not_started;
  const canSubmit = step.status === "not_started" || step.status === "rejected" || step.status === "expired";
  const [open, setOpen] = useState(step.status === "rejected");
  return (
    <li className="rounded-card border border-line p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span aria-hidden="true" className={step.status === "verified"
            ? "flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brass text-xs text-paper"
            : "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-line text-xs text-ink-soft"}>
            {step.status === "verified" ? "✓" : index + 1}
          </span>
          <div>
            <h3 className="text-sm font-medium text-ink">
              {step.title} {!step.required && <span className="font-normal text-ink-soft">(optional)</span>}
            </h3>
            <p className="text-xs text-ink-soft">{WHY[step.key]}</p>
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${chip.className}`}>{chip.label}</span>
      </div>
      {step.status === "rejected" && step.rejection_reason && (
        <p role="alert" className="mt-3 rounded-lg bg-[#fbecea] px-3 py-2 text-xs text-thread">
          Reviewer's note: {step.rejection_reason}
        </p>
      )}
      {(step.status === "pending" || step.status === "under_review") && (
        <p className="mt-3 text-xs text-ink-soft">We're checking your documents. You'll get a notification when it's done.</p>
      )}
      {canSubmit && (
        <div className="mt-3">
          {!open
            ? <button type="button" onClick={() => setOpen(true)} className="text-sm font-medium text-brass-deep underline">
                {step.status === "not_started" ? "Start" : "Resubmit"}
              </button>
            : step.action === "kyc"
              ? <KYCForm onSubmitted={onChanged} />
              : <KYBForm onSubmitted={onChanged} />}
        </div>
      )}
    </li>
  );
}

/** One checklist for every role: what's needed to get the verified badge, and what to do next. */
export function VerificationCenter() {
  const [summary, setSummary] = useState<VerificationSummary | null>(null);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    verificationApi.me().then((data) => { if (active) { setSummary(data); setError(false); } })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [tick]);

  if (error) return <p role="alert" className="text-sm text-thread">Verification details are unavailable. Please refresh.</p>;
  if (!summary) return null;

  const required = summary.steps.filter((s) => s.required);
  const done = required.filter((s) => s.status === "verified").length;

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs text-ink-soft">Verification status</p>
            <p className="font-display text-lg text-ink">{summary.verified ? "You're verified" : "Not verified yet"}</p>
          </div>
          {summary.verified && <VerifiedBadge />}
        </div>
        {required.length > 0 && (
          <div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muslin" role="progressbar"
              aria-valuemin={0} aria-valuemax={required.length} aria-valuenow={done}
              aria-label={`${done} of ${required.length} required checks complete`}>
              <div className="h-full rounded-full bg-brass transition-all" style={{ width: `${(done / required.length) * 100}%` }} />
            </div>
            <p className="mt-1.5 text-xs text-ink-soft">{done} of {required.length} required checks complete</p>
          </div>
        )}
        {summary.next_step && <p className="text-sm text-ink">{summary.next_step}</p>}
        <p className="text-xs text-ink-soft">Verified profiles get the badge customers look for, and only verified shops and riders appear publicly.</p>
      </Card>
      <ol className="flex flex-col gap-3">
        {summary.steps.map((step, index) => (
          <Step key={step.key + step.status} step={step} index={index} onChanged={() => setTick((t) => t + 1)} />
        ))}
      </ol>
    </div>
  );
}
