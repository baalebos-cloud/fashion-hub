import type { ReactNode } from "react";
import { DashboardLayout } from "./DashboardLayout";
import { useAuth } from "@/hooks/use-auth";

/** Shared by both tailors and designers — Sidebar already renders the
 * same nav list for both (see Sidebar.tsx), so this layout just forwards
 * whichever of the two the signed-in user actually is. */
export function ProfessionalLayout({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const role = user?.role === "designer" ? "designer" : "tailor";
  return <DashboardLayout role={role}>{children}</DashboardLayout>;
}
