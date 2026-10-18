import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PaymentSuccess as PaymentSuccessComponent } from "@/components/payments/PaymentSuccess";
import { Button } from "@/components/ui/button";
import { paymentsApi } from "@/api/payments.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Payment } from "@/types/payment";

export function VerifiedPaymentReturn({ ordersPath }: { ordersPath: string }) {
  const [params] = useSearchParams();
  const reference = params.get("reference") || params.get("trxref") || params.get("tx_ref");
  const [result, setResult] = useState<{ reference: string; payment: Payment } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setError(null);
    setResult(null);
    if (reference) {
      setIsVerifying(true);
      paymentsApi.verify(reference)
        .then((payment) => { if (active) setResult({ reference, payment }); })
        .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
        .finally(() => { if (active) setIsVerifying(false); });
    }
    return () => { active = false; };
  }, [reference, attempt]);
  if (reference && result?.reference === reference && result.payment.status === "successful" && !result.payment.requires_review) {
    return <PaymentSuccessComponent ordersPath={ordersPath} />;
  }
  if (reference && result?.reference === reference && result.payment.requires_review) return (
    <div className="mx-auto flex max-w-sm flex-col gap-4 py-12 text-center">
      <h1>Payment received — review required</h1>
      <p role="status">Your payment was received, but the order could not be confirmed. Contact support with reference {reference}. Check your order before paying again.</p>
      <Link to={ordersPath} className="underline">View my orders</Link>
    </div>
  );
  return (
    <div className="mx-auto flex max-w-sm flex-col gap-4 py-12 text-center">
      <h1 className="font-display text-xl text-ink">{isVerifying ? "Confirming payment…" : "Payment not confirmed"}</h1>
      <p role="status" className="text-sm text-ink-soft">
        {!reference ? "No payment reference was supplied. Check your order before starting another payment." : error || (isVerifying ? "Checking the payment provider. Please wait." : `The payment status is ${result?.payment.status ?? "unknown"}. You can check again shortly.`)}
      </p>
      {reference && <Button onClick={() => setAttempt((value) => value + 1)} disabled={isVerifying}>Check payment again</Button>}
      <Link to={ordersPath} className="text-brass-deep underline">View my orders</Link>
    </div>
  );
}
