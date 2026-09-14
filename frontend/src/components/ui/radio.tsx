import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export const Radio = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="radio"
      className={cn("h-4 w-4 border-line text-brass focus:ring-brass", className)}
      {...props}
    />
  )
);
Radio.displayName = "Radio";
