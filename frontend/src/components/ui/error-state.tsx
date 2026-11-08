import type { ReactNode } from "react";
import { Button } from "./button";

/** What went wrong and what to do next, with a retry when one makes sense.
 * Keep the user's input on screen; this replaces only the part that failed to load. */
export function ErrorState({
  title,
  description,
  onRetry,
  retryLabel = "Try again",
  action,
}: {
  title: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  action?: ReactNode;
}) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-2 rounded-card border border-line bg-surface px-6 py-10 text-center">
      <h3 className="font-semibold text-thread">{title}</h3>
      {description && <p className="max-w-sm text-sm text-ink-soft">{description}</p>}
      {(onRetry || action) && (
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {onRetry && <Button variant="secondary" onClick={onRetry}>{retryLabel}</Button>}
          {action}
        </div>
      )}
    </div>
  );
}
