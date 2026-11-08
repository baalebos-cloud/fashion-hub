import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ className, error, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "w-full min-h-11 rounded-control border border-line-strong bg-surface px-3 py-2.5 text-base text-ink",
      "focus:border-indigo focus:outline-2 focus:outline-offset-1 focus:outline-indigo/30 disabled:bg-muslin disabled:text-disabled",
      error && "border-thread bg-danger-wash/40",
      className
    )}
    aria-invalid={Boolean(error)}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
