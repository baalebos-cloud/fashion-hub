import { createBrowserRouter, Outlet, type RouteObject } from "react-router-dom";
import { AuthGuard } from "@/guards/AuthGuard";
import { CustomerGuard } from "@/guards/CustomerGuard";
import { ProfessionalGuard } from "@/guards/ProfessionalGuard";
import { VendorGuard } from "@/guards/VendorGuard";
import { DeliveryGuard } from "@/guards/DeliveryGuard";
import { AdminGuard } from "@/guards/AdminGuard";
import { RouteErrorPage } from "@/components/common/RouteErrorPage";

import { publicRouteObjects } from "./public.routes";
import { authRouteObjects } from "./auth.routes";
import { customerRouteObjects } from "./customer.routes";
import { professionalRouteObjects } from "./professional.routes";
import { vendorRouteObjects } from "./vendor.routes";
import { deliveryRouteObjects } from "./delivery.routes";
import { adminRouteObjects } from "./admin.routes";

/**
 * React Router renders its own fallback for route errors unless a route has
 * an errorElement. The regular React ErrorBoundary in App is not enough.
 * All routes inherit this shared error element, including guarded branches.
 */
export const routeObjects: RouteObject[] = [
  {
    path: "/",
    element: <Outlet />,
    errorElement: <RouteErrorPage />,
    children: [
      ...publicRouteObjects,
      ...authRouteObjects,
      {
        element: <AuthGuard />,
        children: [
          { element: <CustomerGuard />, children: [{ path: "/app/customer", children: customerRouteObjects }] },
          { element: <ProfessionalGuard />, children: [{ path: "/app/professional", children: professionalRouteObjects }] },
          { element: <VendorGuard />, children: [{ path: "/app/vendor", children: vendorRouteObjects }] },
          { element: <DeliveryGuard />, children: [{ path: "/app/delivery", children: deliveryRouteObjects }] },
          { element: <AdminGuard />, children: [{ path: "/app/admin", children: adminRouteObjects }] },
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(routeObjects);
