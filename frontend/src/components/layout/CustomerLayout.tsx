import type { ReactNode } from "react";
import { DashboardLayout } from "./DashboardLayout";

export function CustomerLayout({ children }: { children: ReactNode }) {
  return <DashboardLayout role="customer">{children}</DashboardLayout>;
}
