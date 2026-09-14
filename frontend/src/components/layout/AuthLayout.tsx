import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { publicRoutes } from "@/config/routes.config";

/** Centered card layout for Login/Signup/ForgotPassword/ResetPassword —
 * no header/sidebar chrome, just the brand mark and the form. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muslin px-4">
      <div className="w-full max-w-sm">
        <Link to={publicRoutes.home} className="mb-8 block text-center font-display text-2xl text-ink">
          Fashion Hub
        </Link>
        <div className="rounded-card border border-line bg-paper p-6 shadow-sm">{children}</div>
      </div>
    </div>
  );
}
