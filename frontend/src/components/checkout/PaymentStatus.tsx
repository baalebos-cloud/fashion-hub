import { useEffect, useState } from "react";
import { usePayment } from "@/hooks/use-payment";
import { paymentStatusLabel } from "@/lib/payments/payment-utils";
import { Spinner } from "@/components/ui/spinner";
import type { Payment } from "@/types/payment";

export function PaymentStatus({ providerReference }: { providerReference: string }) {
  const { verifyPayment } = usePayment();
  const [payment, setPayment] = useState<Payment | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    verifyPayment(providerReference)
      .then(setPayment)
      .finally(() => setIsLoading(false));
  }, [providerReference, verifyPayment]);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-ink-soft">
        <Spinner size="sm" /> Confirming your payment…
      </div>
    );
  }

  return <p className="text-sm text-ink">{payment ? paymentStatusLabel(payment.status) : "Unable to confirm payment status."}</p>;
}
