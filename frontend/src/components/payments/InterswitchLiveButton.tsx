import { useState } from "react";
import { paymentsApi } from "@/api/payments.api";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { submitInterswitchCheckout } from "@/lib/interswitchCheckout";

/** Live checkout is a deliberate customer action, never automatic. */
export function InterswitchLiveButton({ orderId, disabled }: { orderId: string; disabled?: boolean }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function checkout() {
    if (submitting || disabled) return;
    setSubmitting(true);
    setError(null);
    try {
      const form = await paymentsApi.initializeLiveInterswitch(orderId);
      submitInterswitchCheckout(form);
    } catch (reason) {
      setError(getDisplayErrorMessage(reason));
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Button className="w-full" isLoading={submitting} disabled={disabled || submitting}
        onClick={() => { void checkout(); }}>
        Pay securely with Interswitch
      </Button>
      {error && <p role="alert" className="mt-2 text-sm text-thread">{error}</p>}
      <p className="mt-1 text-xs text-ink-soft">
        You will complete payment on Interswitch. Your order is confirmed only after independent verification.
      </p>
    </div>
  );
}
