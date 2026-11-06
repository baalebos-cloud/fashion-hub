import type { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { MobileNavigation } from "./MobileNavigation";
import type { UserRole } from "@/types/auth";
import { AccountChecklist } from "@/components/profile/AccountChecklist";

/**
 * Shared shell for every authenticated dashboard (Customer, Professional,
 * Vendor, Delivery, Admin). Role-specific layouts below are thin wrappers
 * around this that exist purely for readability/routing clarity — they
 * don't diverge in structure, only in which `role` they pass to Sidebar.
 */
export function DashboardLayout({ role, children }: { role: UserRole; children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <Header fullWidth leading={<MobileNavigation role={role} />} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar role={role} />
        {/* Bottom padding keeps the floating "Ask Tailora" button from covering the last content. */}
        <main className="flex-1 overflow-y-auto p-4 pb-28 lg:p-8 lg:pb-28"><AccountChecklist />{children}</main>
      </div>
    </div>
  );
}
