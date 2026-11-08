import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";
import { Spinner } from "./spinner";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

// Adire indigo is the one action colour; secondary/ghost/danger never compete with it.
const VARIANT_CLASSES: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "border border-transparent bg-indigo text-surface hover:bg-indigo-deep",
  secondary: "border border-line-strong bg-surface text-ink hover:border-indigo",
  ghost: "border border-transparent bg-transparent text-indigo hover:bg-indigo-wash",
  danger: "border border-thread/30 bg-danger-wash text-thread hover:border-thread",
};

// md is the default 44px touch target; sm (36px) is for dense rows only.
const SIZE_CLASSES: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "min-h-9 text-sm px-3 rounded-control",
  md: "min-h-11 text-[15px] px-4 rounded-control",
  lg: "min-h-12 text-base px-5 rounded-control",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-semibold transition-colors",
        "disabled:cursor-not-allowed disabled:border-line disabled:bg-muslin disabled:text-disabled",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className
      )}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      {...props}
    >
      {isLoading && <Spinner size="sm" />}
      {children}
    </button>
  )
);
Button.displayName = "Button";
