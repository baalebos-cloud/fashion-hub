import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { publicRoutes } from "@/config/routes.config";

/** Split-panel auth layout: dark brand panel left, form right.
 * Collapses to single-column on mobile. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Left decorative panel — hidden on small screens */}
      <div
        aria-hidden="true"
        className="hidden w-1/2 flex-col justify-between bg-ink p-12 lg:flex"
      >
        <Link to={publicRoutes.home} className="font-display text-2xl text-brass">
          Fashion Hub
        </Link>
        <div>
          <blockquote className="font-display text-3xl leading-snug text-paper">
            "The craft of tailoring is the art of listening to a body."
          </blockquote>
          <p className="mt-4 text-sm text-paper/50">— Fashion Hub</p>
        </div>
        <p className="text-xs text-paper/30">© {new Date().getFullYear()} Fashion Hub</p>
      </div>

      {/* Right form panel */}
      <div className="flex flex-1 flex-col items-center justify-center bg-muslin px-4 py-12">
        <Link
          to={publicRoutes.home}
          className="mb-8 block font-display text-2xl text-ink lg:hidden"
        >
          Fashion Hub
        </Link>
        <div className="w-full max-w-sm rounded-card border border-line bg-paper p-6 shadow-sm">
          {children}
        </div>
      </div>
    </div>
  );
}
