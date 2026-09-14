import type { ReactNode } from "react";

/** Shared filter shell — ProfessionalFilters and VendorFilters render
 * their own controls as children of this consistent layout wrapper. */
export function SearchFilters({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-3 rounded-card border border-line p-3">{children}</div>;
}
