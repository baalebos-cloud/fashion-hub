import { useState, type ReactNode } from "react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/**
 * Two-step admin action: open, give a reason (kept in the audit log), confirm.
 * `extra` renders above the reason, e.g. a rider picker for reassignment.
 */
export function DispatchAction({ label, confirmLabel, variant = "secondary", reasonLabel = "Reason (kept in the audit log)",
  minLength = 5, extra, canConfirm = true, onConfirm }: {
  label: string; confirmLabel: string; variant?: ButtonProps["variant"]; reasonLabel?: string; minLength?: number;
  extra?: ReactNode; canConfirm?: boolean; onConfirm: (reason: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return <Button size="sm" variant={variant} onClick={() => setOpen(true)}>{label}</Button>;

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm(reason.trim());
      setOpen(false);
      setReason("");
    } catch (err) {
      setError(getDisplayErrorMessage(err, "That action couldn't be completed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex w-full flex-col gap-2 rounded-lg bg-muslin p-3">
      {extra}
      <label className="text-xs text-ink-soft">
        {reasonLabel}
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} maxLength={500}
          className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink focus:border-brass focus:outline-none" />
      </label>
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" variant={variant === "secondary" ? "primary" : variant} isLoading={busy}
          disabled={!canConfirm || reason.trim().length < minLength} onClick={() => void confirm()}>{confirmLabel}</Button>
        <Button size="sm" variant="ghost" onClick={() => { setOpen(false); setError(null); }}>Cancel</Button>
      </div>
    </div>
  );
}
