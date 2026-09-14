import type { ReactNode } from "react";
import { Header } from "./Header";
import { Footer } from "./Footer";

/** Wraps public marketing pages (Home, FindTailor, ProfessionalProfile,
 * etc.) — header + footer, no role-specific sidebar. Authenticated
 * dashboard routes use DashboardLayout instead. */
export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
