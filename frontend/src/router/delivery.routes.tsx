import type { ComponentType } from "react";
import type { RouteObject } from "react-router-dom";
import { DeliveryLayout } from "@/components/layout/DeliveryLayout";

import Dashboard from "@/pages/delivery/Dashboard";
import DeliveryRequests from "@/pages/delivery/DeliveryRequests";
import ActiveDeliveries from "@/pages/delivery/ActiveDeliveries";
import DeliveryDetails from "@/pages/delivery/DeliveryDetails";
import Pickup from "@/pages/delivery/Pickup";
import Navigation from "@/pages/delivery/Navigation";
import Dropoff from "@/pages/delivery/Dropoff";
import DeliveryHistory from "@/pages/delivery/DeliveryHistory";
import Earnings from "@/pages/delivery/Earnings";
import Verification from "@/pages/delivery/Verification";
import Profile from "@/pages/delivery/Profile";
import Notifications from "@/pages/delivery/Notifications";
import Settings from "@/pages/delivery/Settings";

const withLayout = (Page: ComponentType) => (
  <DeliveryLayout>
    <Page />
  </DeliveryLayout>
);

export const deliveryRouteObjects: RouteObject[] = [
  { index: true, element: withLayout(Dashboard) },
  { path: "requests", element: withLayout(DeliveryRequests) },
  { path: "active", element: withLayout(ActiveDeliveries) },
  { path: ":deliveryId", element: withLayout(DeliveryDetails) },
  { path: ":deliveryId/pickup", element: withLayout(Pickup) },
  { path: ":deliveryId/navigate", element: withLayout(Navigation) },
  { path: ":deliveryId/dropoff", element: withLayout(Dropoff) },
  { path: "history", element: withLayout(DeliveryHistory) },
  { path: "earnings", element: withLayout(Earnings) },
  { path: "verification", element: withLayout(Verification) },
  { path: "profile", element: withLayout(Profile) },
  { path: "notifications", element: withLayout(Notifications) },
  { path: "settings", element: withLayout(Settings) },
];
