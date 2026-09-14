import { paymentConfig } from "@/config/payment.config";

/** Only one provider is active at a time (see PAYMENT_PROVIDER on the
 * backend); this simply confirms which one before redirecting. */
export function PaymentMethod() {
  return (
    <div className="rounded-card border border-line p-3 text-sm text-ink">
      You'll be redirected to <span className="font-medium capitalize">{paymentConfig.provider}</span> to complete payment securely.
    </div>
  );
}
