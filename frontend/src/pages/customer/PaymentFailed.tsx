import { useNavigate } from "react-router-dom";
import { PaymentFailed as PaymentFailedComponent } from "@/components/payments/PaymentFailed";
import { customerRoutes } from "@/config/routes.config";

export default function PaymentFailed() {
  const navigate = useNavigate();
  return <PaymentFailedComponent onRetry={() => navigate(customerRoutes.orders)} />;
}
