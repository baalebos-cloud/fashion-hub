import { env } from "./environment";

/**
 * Client-side payment config. Only ever holds a PUBLIC/publishable key —
 * the secret key lives exclusively on the backend
 * (see backend/app/integrations/payments/). The frontend's job is to
 * collect card details via the provider's own hosted widget/redirect and
 * hand control back to the backend for verification; it never computes or
 * trusts a "payment succeeded" state on its own.
 */
export const paymentConfig = {
  provider: env.paymentProvider as "paystack" | "flutterwave",
  publicKey: env.paymentPublicKey,
} as const;
