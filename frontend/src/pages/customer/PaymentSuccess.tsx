import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PaymentSuccess as PaymentSuccessComponent } from "@/components/payments/PaymentSuccess";
import { Button } from "@/components/ui/button";
import { paymentsApi } from "@/api/payments.api";
import { customerRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Payment } from "@/types/payment";

export default function PaymentSuccess() {
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
  if (reference && result?.reference === reference && result.payment.status === "successful") {
    return <PaymentSuccessComponent ordersPath={customerRoutes.orders} />;
  }
  return (
    <div className="mx-auto flex max-w-sm flex-col gap-4 py-12 text-center">
      <h1 className="font-display text-xl text-ink">{isVerifying ? "Confirming payment…" : "Payment not confirmed"}</h1>
      <p role="status" className="text-sm text-ink-soft">
        {!reference ? "No payment reference was supplied. Check your order before starting another payment." : error || (isVerifying ? "Checking the payment provider. Please wait." : `The payment status is ${result?.payment.status ?? "unknown"}. You can check again shortly.`)}
      </p>
      {reference && <Button onClick={() => setAttempt((value) => value + 1)} disabled={isVerifying}>Check payment again</Button>}
      <Link to={customerRoutes.orders} className="text-brass-deep underline">View my orders</Link>
    </div>
  );
}
