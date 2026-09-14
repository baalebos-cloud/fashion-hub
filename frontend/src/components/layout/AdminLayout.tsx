import type { ReactNode } from "react";
import { DashboardLayout } from "./DashboardLayout";

export function AdminLayout({ children }: { children: ReactNode }) {
  return <DashboardLayout role="admin">{children}</DashboardLayout>;
}
