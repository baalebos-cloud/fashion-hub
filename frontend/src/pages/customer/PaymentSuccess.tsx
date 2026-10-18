import { VerifiedPaymentReturn } from "@/components/payments/VerifiedPaymentReturn";
import { customerRoutes } from "@/config/routes.config";
export default function PaymentSuccess() { return <VerifiedPaymentReturn ordersPath={customerRoutes.orders} />; }
