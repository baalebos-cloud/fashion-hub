import type { ReactNode } from "react";
import { DashboardLayout } from "./DashboardLayout";

export function VendorLayout({ children }: { children: ReactNode }) {
  return <DashboardLayout role="vendor">{children}</DashboardLayout>;
}
