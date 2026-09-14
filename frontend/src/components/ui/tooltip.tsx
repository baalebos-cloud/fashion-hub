import { type ReactNode, useState } from "react";
import { cn } from "@/lib/utils/cn";

export function Tooltip({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <span
          role="tooltip"
          className={cn(
            "absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-xs text-paper",
            className
          )}
        >
          {label}
        </span>
      )}
    </span>
  );
}
