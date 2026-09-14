import { createBrowserRouter } from "react-router-dom";
import { AuthGuard } from "@/guards/AuthGuard";
import { CustomerGuard } from "@/guards/CustomerGuard";
import { ProfessionalGuard } from "@/guards/ProfessionalGuard";
import { VendorGuard } from "@/guards/VendorGuard";
import { DeliveryGuard } from "@/guards/DeliveryGuard";
import { AdminGuard } from "@/guards/AdminGuard";

import { publicRouteObjects } from "./public.routes";
import { authRouteObjects } from "./auth.routes";
import { customerRouteObjects } from "./customer.routes";
import { professionalRouteObjects } from "./professional.routes";
import { vendorRouteObjects } from "./vendor.routes";
import { deliveryRouteObjects } from "./delivery.routes";
import { adminRouteObjects } from "./admin.routes";

/**
 * The full route tree. Every /app/* branch is wrapped first in AuthGuard
 * (must be logged in at all) and then in the matching RoleGuard subclass
 * (must be THIS role) — see guards/ for what these actually enforce and,
 * just as importantly, what they don't (they are not the security
 * boundary; the backend independently authorizes every request regardless
 * of what route the frontend rendered).
 */
export const router = createBrowserRouter([
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
]);
