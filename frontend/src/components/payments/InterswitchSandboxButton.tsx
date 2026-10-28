import { useState } from "react";
import { paymentsApi } from "@/api/payments.api";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { submitInterswitchCheckout } from "@/lib/interswitchCheckout";

/** Explicit user action only; API derives price and reference from the order. */
export function InterswitchSandboxButton({
  orderId,
  disabled,
}: {
  orderId: string;
  disabled?: boolean;
}) {
  const [isSubmitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheckout() {
    setSubmitting(true);
    setError(null);
    try {
      const checkout = await paymentsApi.initializeInterswitch(orderId);
      submitInterswitchCheckout(checkout);
    } catch (exception) {
      setError(getDisplayErrorMessage(exception));
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-3">
      <Button
        className="w-full"
        disabled={disabled || isSubmitting}
        isLoading={isSubmitting}
        onClick={() => { void handleCheckout(); }}
      >
        Pay with Interswitch (sandbox)
      </Button>
      {error && <p className="mt-2 text-sm text-thread" role="alert">{error}</p>}
      <p className="mt-1 text-xs text-ink-soft">
        Test environment only. Payment is confirmed after a separate server check.
      </p>
    </div>
  );
}
