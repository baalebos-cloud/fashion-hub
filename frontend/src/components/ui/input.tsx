import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({ className, error, id, ...props }, ref) => (
  <input
    ref={ref}
    id={id}
    className={cn(
      "w-full min-h-11 rounded-control border border-line-strong bg-surface px-3 py-2.5 text-base text-ink placeholder:text-ink-soft/70",
      "focus:border-indigo focus:outline-2 focus:outline-offset-1 focus:outline-indigo/30 disabled:bg-muslin disabled:text-disabled",
      error && "border-thread bg-danger-wash/40",
      className
    )}
    aria-invalid={Boolean(error)}
    {...props}
  />
));
Input.displayName = "Input";
