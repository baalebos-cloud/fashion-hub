import { VerifiedPaymentReturn } from "@/components/payments/VerifiedPaymentReturn";
import { professionalRoutes } from "@/config/routes.config";
export default function VendorPaymentSuccess() { return <VerifiedPaymentReturn ordersPath={professionalRoutes.vendorOrders} />; }
