import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ className, error, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink",
      "focus:border-brass focus:outline-none",
      error && "border-thread",
      className
    )}
    aria-invalid={Boolean(error)}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
