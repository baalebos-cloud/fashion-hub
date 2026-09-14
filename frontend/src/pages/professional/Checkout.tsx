import { useState } from "react";
import { CheckoutPage } from "@/components/checkout/CheckoutPage";
import { professionalRoutes } from "@/config/routes.config";
import type { Address } from "@/types/location";

export default function Checkout() {
  const [addresses] = useState<Address[]>([]);
  const callbackUrl = `${window.location.origin}${professionalRoutes.vendorOrders}`;

  return <CheckoutPage addresses={addresses} paymentCallbackUrl={callbackUrl} />;
}
