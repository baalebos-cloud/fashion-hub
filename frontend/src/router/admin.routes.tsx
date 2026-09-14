import type { ComponentType } from "react";
import type { RouteObject } from "react-router-dom";
import { AdminLayout } from "@/components/layout/AdminLayout";

import Dashboard from "@/pages/admin/Dashboard";
import Users from "@/pages/admin/Users";
import Customers from "@/pages/admin/Customers";
import Professionals from "@/pages/admin/Professionals";
import Vendors from "@/pages/admin/Vendors";
import DeliveryPartners from "@/pages/admin/DeliveryPartners";
import Orders from "@/pages/admin/Orders";
import Payments from "@/pages/admin/Payments";
import Invoices from "@/pages/admin/Invoices";
import Deliveries from "@/pages/admin/Deliveries";
import KYC from "@/pages/admin/KYC";
import KYB from "@/pages/admin/KYB";
import Reviews from "@/pages/admin/Reviews";
import Disputes from "@/pages/admin/Disputes";
import Reports from "@/pages/admin/Reports";
import AuditLogs from "@/pages/admin/AuditLogs";
import Notifications from "@/pages/admin/Notifications";
import Settings from "@/pages/admin/Settings";

const withLayout = (Page: ComponentType) => (
  <AdminLayout>
    <Page />
  </AdminLayout>
);

export const adminRouteObjects: RouteObject[] = [
  { index: true, element: withLayout(Dashboard) },
  { path: "users", element: withLayout(Users) },
  { path: "customers", element: withLayout(Customers) },
  { path: "professionals", element: withLayout(Professionals) },
  { path: "vendors", element: withLayout(Vendors) },
  { path: "delivery-partners", element: withLayout(DeliveryPartners) },
  { path: "orders", element: withLayout(Orders) },
  { path: "payments", element: withLayout(Payments) },
  { path: "invoices", element: withLayout(Invoices) },
  { path: "deliveries", element: withLayout(Deliveries) },
  { path: "kyc", element: withLayout(KYC) },
  { path: "kyb", element: withLayout(KYB) },
  { path: "reviews", element: withLayout(Reviews) },
  { path: "disputes", element: withLayout(Disputes) },
  { path: "reports", element: withLayout(Reports) },
  { path: "audit-logs", element: withLayout(AuditLogs) },
  { path: "notifications", element: withLayout(Notifications) },
  { path: "settings", element: withLayout(Settings) },
];
