import type { ReactNode } from "react";
import { DashboardLayout } from "./DashboardLayout";
import { RiderSharingProvider } from "@/components/delivery/RiderSharingProvider";

export function DeliveryLayout({ children }: { children: ReactNode }) {
  // Location sharing lives here so it keeps running across all of the rider's screens.
  return (
    <RiderSharingProvider>
      <DashboardLayout role="delivery_partner">{children}</DashboardLayout>
    </RiderSharingProvider>
  );
}
