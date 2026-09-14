import type { ComponentType } from "react";
import type { RouteObject } from "react-router-dom";
import { CustomerLayout } from "@/components/layout/CustomerLayout";

import Dashboard from "@/pages/customer/Dashboard";
import Orders from "@/pages/customer/Orders";
import OrderDetails from "@/pages/customer/OrderDetails";
import TrackOrder from "@/pages/customer/TrackOrder";
import FindProfessionals from "@/pages/customer/FindProfessionals";
import ProfessionalDetails from "@/pages/customer/ProfessionalDetails";
import CreateOrder from "@/pages/customer/CreateOrder";
import Measurements from "@/pages/customer/Measurements";
import Designs from "@/pages/customer/Designs";
import Cart from "@/pages/customer/Cart";
import Checkout from "@/pages/customer/Checkout";
import Payment from "@/pages/customer/Payment";
import PaymentSuccess from "@/pages/customer/PaymentSuccess";
import PaymentFailed from "@/pages/customer/PaymentFailed";
import Invoices from "@/pages/customer/Invoices";
import InvoiceDetails from "@/pages/customer/InvoiceDetails";
import Reviews from "@/pages/customer/Reviews";
import Favorites from "@/pages/customer/Favorites";
import Notifications from "@/pages/customer/Notifications";
import Messages from "@/pages/customer/Messages";
import Profile from "@/pages/customer/Profile";
import Addresses from "@/pages/customer/Addresses";
import Settings from "@/pages/customer/Settings";

const withLayout = (Page: ComponentType) => (
  <CustomerLayout>
    <Page />
  </CustomerLayout>
);

/** Paths are relative to customerRoutes.dashboard ("/app/customer"), which
 * is where CustomerGuard mounts this array in router/index.tsx. */
export const customerRouteObjects: RouteObject[] = [
  { index: true, element: withLayout(Dashboard) },
  { path: "orders", element: withLayout(Orders) },
  { path: "orders/:orderId", element: withLayout(OrderDetails) },
  { path: "orders/:orderId/track", element: withLayout(TrackOrder) },
  { path: "find", element: withLayout(FindProfessionals) },
  { path: "professionals/:professionalId", element: withLayout(ProfessionalDetails) },
  { path: "professionals/:professionalId/order", element: withLayout(CreateOrder) },
  { path: "measurements", element: withLayout(Measurements) },
  { path: "designs", element: withLayout(Designs) },
  { path: "cart", element: withLayout(Cart) },
  { path: "checkout", element: withLayout(Checkout) },
  { path: "orders/:orderId/payment", element: withLayout(Payment) },
  { path: "payment/success", element: withLayout(PaymentSuccess) },
  { path: "payment/failed", element: withLayout(PaymentFailed) },
  { path: "invoices", element: withLayout(Invoices) },
  { path: "invoices/:invoiceId", element: withLayout(InvoiceDetails) },
  { path: "reviews", element: withLayout(Reviews) },
  { path: "favorites", element: withLayout(Favorites) },
  { path: "notifications", element: withLayout(Notifications) },
  { path: "messages", element: withLayout(Messages) },
  { path: "profile", element: withLayout(Profile) },
  { path: "addresses", element: withLayout(Addresses) },
  { path: "settings", element: withLayout(Settings) },
];
