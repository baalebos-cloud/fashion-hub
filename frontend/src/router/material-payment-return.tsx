import { Navigate, useLocation, useParams } from "react-router-dom";
import { useAuthStore } from "@/store/auth.store";
import { materialRoutesFor } from "@/lib/routes/material-routes";
import { LoadingScreen } from "@/components/common/LoadingScreen";

/** After paying for materials, open the buyer's own payment result (customer or tailor/designer),
 * keeping the payment reference. */
export function MaterialPaymentReturn() {
  const { search } = useLocation();
  const user = useAuthStore((state) => state.user);
  if (!user) return <LoadingScreen label="Checking your payment…" />;
  const routes = materialRoutesFor(user.role);
  return <Navigate to={`${routes ? routes.paymentSuccess : "/app"}${search}`} replace />;
}

/** A product opened from the public marketplace before signing in: show it in the buyer's own area,
 * where it can be added to the cart. */
export function MaterialProductReturn() {
  const { productId = "" } = useParams<{ productId: string }>();
  const user = useAuthStore((state) => state.user);
  if (!user) return <LoadingScreen label="Opening the product…" />;
  const routes = materialRoutesFor(user.role);
  return <Navigate to={routes ? routes.productDetails(productId) : `/products/${productId}`} replace />;
}
