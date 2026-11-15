import { VerifiedPaymentReturn } from "@/components/payments/VerifiedPaymentReturn";
import { useMaterialRoutes } from "@/lib/routes/material-routes";
export default function VendorPaymentSuccess() { return <VerifiedPaymentReturn ordersPath={useMaterialRoutes().orders} />; }
