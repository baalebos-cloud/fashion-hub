import type { ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

/** Label above, help or error below, wired up for screen readers.
 * Pass the control's id as `htmlFor`; give the control `aria-describedby={`${htmlFor}-hint`}`. */
export function Field({
  label,
  htmlFor,
  help,
  error,
  optional,
  className,
  children,
}: {
  label: string;
  htmlFor: string;
  help?: string;
  error?: string;
  optional?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="text-sm font-semibold text-ink">
        {label}
        {optional && <span className="ml-1 font-normal text-ink-soft">(optional)</span>}
      </label>
      {children}
      {(error || help) && (
        <p id={`${htmlFor}-hint`} className={cn("text-[13px]", error ? "text-thread" : "text-ink-soft")} role={error ? "alert" : undefined}>
          {error ?? help}
        </p>
      )}
    </div>
  );
}
