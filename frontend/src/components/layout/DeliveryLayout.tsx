import type { ReactNode } from "react";
import { DashboardLayout } from "./DashboardLayout";

export function DeliveryLayout({ children }: { children: ReactNode }) {
  return <DashboardLayout role="delivery_partner">{children}</DashboardLayout>;
}
