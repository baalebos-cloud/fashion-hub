import { useState } from "react";
import { useCart } from "@/hooks/use-cart";
import { useCheckout } from "@/hooks/use-checkout";
import { usePayment } from "@/hooks/use-payment";
import { DeliveryAddress } from "./DeliveryAddress";
import { CheckoutSummary } from "./CheckoutSummary";
import { PaymentMethod } from "./PaymentMethod";
import { PaymentConsent } from "@/components/payments/PaymentConsent";
import { Button } from "@/components/ui/button";
import type { Address } from "@/types/location";

export interface CheckoutPageProps {
  addresses: Address[];
  paymentCallbackUrl: string;
}

export function CheckoutPage({ addresses, paymentCallbackUrl }: CheckoutPageProps) {
  const { summary } = useCart();
  const { submit, isSubmitting, error } = useCheckout();
  const { payAndRedirect, isInitializing } = usePayment();

  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(addresses[0]?.id ?? null);
  const [hasConsented, setHasConsented] = useState(false);

  async function handlePlaceOrder() {
    if (!summary || !selectedAddressId) return;
    const orders = await submit(summary.cart_id, selectedAddressId);
    if (orders.length === 0) return;
    // Multi-vendor checkout produces one order per vendor but a single
    // combined payment — see backend/docs/checkout.md.
    await payAndRedirect(orders[0].id, paymentCallbackUrl);
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Checkout</h1>

      <div>
        <h2 className="mb-2 text-sm font-medium text-ink-soft">Delivery address</h2>
        <DeliveryAddress addresses={addresses} selectedId={selectedAddressId} onSelect={setSelectedAddressId} onAddNew={() => {}} />
      </div>

      <CheckoutSummary />
      <PaymentMethod />
      <PaymentConsent checked={hasConsented} onChange={setHasConsented} />

      {error && <p className="text-sm text-thread">{error}</p>}

      <Button
        onClick={handlePlaceOrder}
        isLoading={isSubmitting || isInitializing}
        disabled={!selectedAddressId || !hasConsented}
        className="w-full"
      >
        Place order &amp; pay
      </Button>
    </div>
  );
}
