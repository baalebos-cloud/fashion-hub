import type { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { MobileNavigation } from "./MobileNavigation";
import type { UserRole } from "@/types/auth";

/**
 * Shared shell for every authenticated dashboard (Customer, Professional,
 * Vendor, Delivery, Admin). Role-specific layouts below are thin wrappers
 * around this that exist purely for readability/routing clarity — they
 * don't diverge in structure, only in which `role` they pass to Sidebar.
 */
export function DashboardLayout({ role, children }: { role: UserRole; children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center border-b border-line px-2 lg:hidden">
        <MobileNavigation role={role} />
      </div>
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar role={role} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
