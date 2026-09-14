import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";
import type { StatusTone } from "@/constants/order-status";

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "bg-muslin text-ink-soft",
  info: "bg-[#e6ecff] text-[#2c3e9e]",
  success: "bg-[#e5f3ea] text-[#256a3f]",
  warning: "bg-[#fbf0dd] text-[#8a5f1f]",
  danger: "bg-[#fbeceA] text-thread",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: StatusTone }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium", TONE_CLASSES[tone], className)}
      {...props}
    />
  );
}
