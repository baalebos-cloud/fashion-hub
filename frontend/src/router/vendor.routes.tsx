import type { ComponentType } from "react";
import type { RouteObject } from "react-router-dom";
import { VendorLayout } from "@/components/layout/VendorLayout";

import Dashboard from "@/pages/vendor/Dashboard";
import Orders from "@/pages/vendor/Orders";
import OrderDetails from "@/pages/vendor/OrderDetails";
import Products from "@/pages/vendor/Products";
import AddProduct from "@/pages/vendor/AddProduct";
import EditProduct from "@/pages/vendor/EditProduct";
import ProductDetails from "@/pages/vendor/ProductDetails";
import Categories from "@/pages/vendor/Categories";
import Inventory from "@/pages/vendor/Inventory";
import Delivery from "@/pages/vendor/Delivery";
import TrackDelivery from "@/pages/vendor/TrackDelivery";
import Invoices from "@/pages/vendor/Invoices";
import Payments from "@/pages/vendor/Payments";
import Verification from "@/pages/vendor/Verification";
import Profile from "@/pages/vendor/Profile";
import Notifications from "@/pages/vendor/Notifications";
import Settings from "@/pages/vendor/Settings";

const withLayout = (Page: ComponentType) => (
  <VendorLayout>
    <Page />
  </VendorLayout>
);

export const vendorRouteObjects: RouteObject[] = [
  { index: true, element: withLayout(Dashboard) },
  { path: "orders", element: withLayout(Orders) },
  { path: "orders/:orderId", element: withLayout(OrderDetails) },
  { path: "products", element: withLayout(Products) },
  { path: "products/new", element: withLayout(AddProduct) },
  { path: "products/:productId/edit", element: withLayout(EditProduct) },
  { path: "products/:productId", element: withLayout(ProductDetails) },
  { path: "categories", element: withLayout(Categories) },
  { path: "inventory", element: withLayout(Inventory) },
  { path: "delivery", element: withLayout(Delivery) },
  { path: "delivery/:deliveryId/track", element: withLayout(TrackDelivery) },
  { path: "invoices", element: withLayout(Invoices) },
  { path: "payments", element: withLayout(Payments) },
  { path: "verification", element: withLayout(Verification) },
  { path: "profile", element: withLayout(Profile) },
  { path: "notifications", element: withLayout(Notifications) },
  { path: "settings", element: withLayout(Settings) },
];
