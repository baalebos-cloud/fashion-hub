import { customerRoutes, professionalRoutes } from "@/config/routes.config";
import { useAuthStore } from "@/store/auth.store";
import type { PaymentReturn } from "@/lib/payments/return-url";

/** Where the materials (fabric and accessories) shopping pages live for a buyer. Customers, tailors
 * and designers share the same pages; only the addresses differ. */
export interface MaterialRoutes {
  marketplace: string;
  productDetails: (id: string) => string;
  cart: string;
  checkout: string;
  paymentSuccess: string;
  orders: string;
  orderDetails: (id: string) => string;
  /** Where the payment provider returns to (see lib/payments/return-url.ts). */
  paymentReturn: PaymentReturn;
  /** Tailors' material orders can be linked to one of their customer orders. */
  linkedCustomerOrder: ((id: string) => string) | null;
}

export const CUSTOMER_MATERIAL_ROUTES: MaterialRoutes = {
  marketplace: customerRoutes.materials,
  productDetails: customerRoutes.materialDetails,
  cart: customerRoutes.cart,
  checkout: customerRoutes.checkout,
  paymentSuccess: customerRoutes.materialPaymentSuccess,
  orders: customerRoutes.materialOrders,
  orderDetails: customerRoutes.materialOrderDetails,
  paymentReturn: "materials",
  linkedCustomerOrder: null,
};

export const PROFESSIONAL_MATERIAL_ROUTES: MaterialRoutes = {
  marketplace: professionalRoutes.vendorMarketplace,
  productDetails: professionalRoutes.vendorProductDetails,
  cart: professionalRoutes.cart,
  checkout: professionalRoutes.checkout,
  paymentSuccess: professionalRoutes.vendorPaymentSuccess,
  orders: professionalRoutes.vendorOrders,
  orderDetails: professionalRoutes.vendorOrderDetails,
  paymentReturn: "vendor",
  linkedCustomerOrder: professionalRoutes.orderDetails,
};

/** Roles that can buy materials. */
export const MATERIAL_BUYER_ROLES = ["customer", "tailor", "designer"] as const;

export function materialRoutesFor(role: string | null | undefined): MaterialRoutes | null {
  if (role === "customer") return CUSTOMER_MATERIAL_ROUTES;
  if (role === "tailor" || role === "designer") return PROFESSIONAL_MATERIAL_ROUTES;
  return null;
}

/** The signed-in buyer's materials pages (professional ones as a fallback while loading). */
export function useMaterialRoutes(): MaterialRoutes {
  const role = useAuthStore((state) => state.user?.role);
  return materialRoutesFor(role) ?? PROFESSIONAL_MATERIAL_ROUTES;
}
