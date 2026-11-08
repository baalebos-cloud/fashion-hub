import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export const Radio = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="radio"
      className={cn("h-4 w-4 border-line-strong text-indigo accent-[var(--tl-indigo)] focus:ring-indigo", className)}
      {...props}
    />
  )
);
Radio.displayName = "Radio";
