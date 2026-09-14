import { PaymentSuccess as PaymentSuccessComponent } from "@/components/payments/PaymentSuccess";
import { customerRoutes } from "@/config/routes.config";

export default function PaymentSuccess() {
  return <PaymentSuccessComponent ordersPath={customerRoutes.orders} />;
}
