import { isApiError } from "@/lib/api/errors";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/** The backend allows this many wrong codes per delivery, across all devices, then locks. */
export const MAX_CODE_ATTEMPTS = 5;

export type CodeOutcome =
  | { kind: "wrong"; message: string }
  | { kind: "locked"; message: string }
  | { kind: "other"; message: string };

/** Turns a failed confirm into what the rider should see. Wrong codes are counted on this
 * device only (other devices may have used tries too), so the screen says "at most". */
export function codeOutcome(err: unknown): CodeOutcome {
  const message = getDisplayErrorMessage(err);
  if (isApiError(err) && err.status === 403) {
    return { kind: "locked", message: "Too many incorrect codes. This handover is locked; report a problem so support can help." };
  }
  if (/incorrect/i.test(message)) return { kind: "wrong", message };
  return { kind: "other", message };
}

/** Large, empty-by-default code field. The rider never sees the customer's code; they type
 * what the customer reads out. */
export function CodeEntry({
  id,
  label,
  value,
  onChange,
  hint,
  wrongCount,
  locked,
  message,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (next: string) => void;
  hint: string;
  wrongCount: number;
  locked: boolean;
  message?: string | null;
}) {
  const triesLeft = Math.max(0, MAX_CODE_ATTEMPTS - wrongCount);
  const bad = locked || wrongCount > 0 || Boolean(message);
  const status = locked
    ? "Too many incorrect codes. This handover is locked; report a problem so support can help."
    : wrongCount > 0
      ? `${message ?? "That code doesn't match."} At most ${triesLeft} ${triesLeft === 1 ? "try" : "tries"} left.`
      : message;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-semibold text-ink">{label}</label>
      <input id={id} aria-label={label} value={value} inputMode="numeric" autoComplete="one-time-code"
        maxLength={6} placeholder="• • • • • •" disabled={locked}
        aria-invalid={bad} aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
        className={`min-h-14 w-full rounded-control border bg-surface px-3 text-center font-mono text-2xl tracking-[0.4em] text-ink placeholder:text-ink-soft/50 focus:outline-2 focus:outline-indigo/30 disabled:bg-muslin disabled:text-disabled ${bad ? "border-thread" : "border-line-strong focus:border-indigo"}`} />
      <p id={`${id}-hint`} role={status ? "alert" : undefined} className={`text-[13px] ${status ? "text-thread" : "text-ink-soft"}`}>
        {status ?? hint}
      </p>
    </div>
  );
}
