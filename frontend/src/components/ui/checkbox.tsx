import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="checkbox"
      className={cn("h-4 w-4 rounded border-line-strong text-indigo accent-[var(--tl-indigo)] focus:ring-indigo", className)}
      {...props}
    />
  )
);
Checkbox.displayName = "Checkbox";
