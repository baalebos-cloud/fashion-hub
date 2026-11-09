import { customerRoutes, professionalRoutes } from "@/config/routes.config";
import { isNativeApp } from "@/lib/native/platform";

/**
 * Where the payment provider sends people back after paying.
 *
 * Website: straight to the payment result page on this site.
 * Phone app: the provider's page opens in the phone's browser, which can't return to the app's own
 * address (capacitor://localhost, which the backend also refuses). So it returns to a small public page
 * on the website (/payment/app-return) that reopens the app on the payment result with a tailora://
 * link. The app then confirms the payment with the backend as usual; the provider's webhook confirms
 * it either way.
 */
export const PAYMENT_RETURN_PATHS = {
  customer: customerRoutes.paymentSuccess,
  vendor: professionalRoutes.vendorPaymentSuccess,
} as const;
export type PaymentReturn = keyof typeof PAYMENT_RETURN_PATHS;

const DEFAULT_SITE = "https://fashion-hub-tawny.vercel.app";

export function siteUrl(): string {
  return (import.meta.env.VITE_PUBLIC_SITE_URL || DEFAULT_SITE).replace(/\/+$/, "");
}

export function paymentCallbackUrl(kind: PaymentReturn): string {
  return isNativeApp()
    ? `${siteUrl()}/payment/app-return?for=${kind}`
    : `${window.location.origin}${PAYMENT_RETURN_PATHS[kind]}`;
}

/** tailora:// link back into the app's payment result, carrying only the payment reference. */
export function appReturnLink(kind: string | null, search: URLSearchParams): string | null {
  if (kind !== "customer" && kind !== "vendor") return null;
  const reference = search.get("reference") || search.get("trxref") || search.get("tx_ref") || "";
  const query = /^[A-Za-z0-9_.-]{1,100}$/.test(reference) ? `?reference=${encodeURIComponent(reference)}` : "";
  return `tailora://app${PAYMENT_RETURN_PATHS[kind].replace(/^\/app/, "")}${query}`;
}
