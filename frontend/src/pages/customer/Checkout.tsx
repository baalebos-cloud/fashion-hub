import { Navigate } from "react-router-dom";
import { customerRoutes } from "@/config/routes.config";

/** Customer checkout happens inline as part of CreateOrder -> Payment;
 * redirect here to keep the route defined without duplicating that flow. */
export default function Checkout() {
  return <Navigate to={customerRoutes.findProfessionals} replace />;
}
