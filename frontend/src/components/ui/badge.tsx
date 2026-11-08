import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";
import type { StatusTone } from "@/constants/order-status";

// Status always reads as a word as well as a colour; every pair is at least 4.5:1.
const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "bg-muslin text-ink-soft",
  info: "bg-indigo-wash text-indigo",
  success: "bg-success-wash text-success",
  warning: "bg-warning-wash text-warning",
  danger: "bg-danger-wash text-thread",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: StatusTone }) {
  return (
    <span
      className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold", TONE_CLASSES[tone], className)}
      {...props}
    />
  );
}
