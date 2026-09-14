import type { ComponentType } from "react";
import type { RouteObject } from "react-router-dom";
import { ProfessionalLayout } from "@/components/layout/ProfessionalLayout";

import Dashboard from "@/pages/professional/Dashboard";
import Orders from "@/pages/professional/Orders";
import OrderDetails from "@/pages/professional/OrderDetails";
import Production from "@/pages/professional/Production";
import Customers from "@/pages/professional/Customers";
import CustomerDetails from "@/pages/professional/CustomerDetails";
import Measurements from "@/pages/professional/Measurements";
import Designs from "@/pages/professional/Designs";
import Portfolio from "@/pages/professional/Portfolio";
import Services from "@/pages/professional/Services";
import VendorMarketplace from "@/pages/professional/VendorMarketplace";
import VendorProductDetails from "@/pages/professional/VendorProductDetails";
import Cart from "@/pages/professional/Cart";
import Checkout from "@/pages/professional/Checkout";
import VendorOrders from "@/pages/professional/VendorOrders";
import VendorOrderDetails from "@/pages/professional/VendorOrderDetails";
import Delivery from "@/pages/professional/Delivery";
import TrackDelivery from "@/pages/professional/TrackDelivery";
import Invoices from "@/pages/professional/Invoices";
import Payments from "@/pages/professional/Payments";
import Reviews from "@/pages/professional/Reviews";
import Verification from "@/pages/professional/Verification";
import Location from "@/pages/professional/Location";
import Messages from "@/pages/professional/Messages";
import Notifications from "@/pages/professional/Notifications";
import Profile from "@/pages/professional/Profile";
import Settings from "@/pages/professional/Settings";

const withLayout = (Page: ComponentType) => (
  <ProfessionalLayout>
    <Page />
  </ProfessionalLayout>
);

/** Mounted at /app/professional by both the "tailor" and "designer" roles
 * — see guards/ProfessionalGuard.tsx. */
export const professionalRouteObjects: RouteObject[] = [
  { index: true, element: withLayout(Dashboard) },
  { path: "orders", element: withLayout(Orders) },
  { path: "orders/:orderId", element: withLayout(OrderDetails) },
  { path: "production", element: withLayout(Production) },
  { path: "customers", element: withLayout(Customers) },
  { path: "customers/:customerId", element: withLayout(CustomerDetails) },
  { path: "measurements", element: withLayout(Measurements) },
  { path: "designs", element: withLayout(Designs) },
  { path: "portfolio", element: withLayout(Portfolio) },
  { path: "services", element: withLayout(Services) },
  { path: "vendor-marketplace", element: withLayout(VendorMarketplace) },
  { path: "vendor-marketplace/products/:productId", element: withLayout(VendorProductDetails) },
  { path: "cart", element: withLayout(Cart) },
  { path: "checkout", element: withLayout(Checkout) },
  { path: "vendor-orders", element: withLayout(VendorOrders) },
  { path: "vendor-orders/:orderId", element: withLayout(VendorOrderDetails) },
  { path: "delivery", element: withLayout(Delivery) },
  { path: "delivery/:deliveryId/track", element: withLayout(TrackDelivery) },
  { path: "invoices", element: withLayout(Invoices) },
  { path: "payments", element: withLayout(Payments) },
  { path: "reviews", element: withLayout(Reviews) },
  { path: "verification", element: withLayout(Verification) },
  { path: "location", element: withLayout(Location) },
  { path: "messages", element: withLayout(Messages) },
  { path: "notifications", element: withLayout(Notifications) },
  { path: "profile", element: withLayout(Profile) },
  { path: "settings", element: withLayout(Settings) },
];
