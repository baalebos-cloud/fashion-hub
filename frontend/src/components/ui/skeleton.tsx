import { useEffect, useState } from "react";
import { cn } from "@/lib/utils/cn";
import { Button } from "./button";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-muslin", className)} aria-hidden="true" />;
}

/** Skeleton rows shaped like a list, used instead of a spinner. On slow connections it says
 * so after `slowAfterMs` and offers a retry. */
export function SkeletonRows({
  rows = 3,
  label = "Loading",
  slowAfterMs = 8000,
  onRetry,
}: {
  rows?: number;
  label?: string;
  slowAfterMs?: number;
  onRetry?: () => void;
}) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), slowAfterMs);
    return () => clearTimeout(timer);
  }, [slowAfterMs]);

  return (
    <div role="status" aria-label={label} className="flex flex-col gap-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
          <Skeleton className="h-3.5 w-2/5" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      ))}
      {slow && (
        <div className="flex flex-wrap items-center gap-3 text-sm text-ink-soft">
          Still loading…
          {onRetry && <Button size="sm" variant="secondary" onClick={onRetry}>Retry</Button>}
        </div>
      )}
    </div>
  );
}
