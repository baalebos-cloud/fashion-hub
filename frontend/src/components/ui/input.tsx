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
      "w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink placeholder:text-ink-soft/60",
      "focus:border-brass focus:outline-none",
      error && "border-thread",
      className
    )}
    aria-invalid={Boolean(error)}
    {...props}
  />
));
Input.displayName = "Input";
