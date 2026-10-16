import { useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { PaymentButton } from "@/components/payments/PaymentButton";
import { PaymentSummary } from "@/components/payments/PaymentSummary";
import { PaymentConsent } from "@/components/payments/PaymentConsent";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { customerRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";
import { useState } from "react";

export default function Payment() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, isLoading } = useOrder(orderId);
  const [hasConsented, setHasConsented] = useState(false);

  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;

  const callbackUrl = `${window.location.origin}${customerRoutes.paymentSuccess}`;

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Complete payment</h1>
      <ul className="divide-y divide-line">{order.items.map((item) => <li key={item.id} className="flex justify-between py-2 text-sm"><span>{item.name_snapshot} × {item.quantity}</span><span>{formatCurrency(item.line_total, order.currency)}</span></li>)}</ul>
      <PaymentSummary orderNumber={order.order_number} amount={order.total_amount} currency={order.currency} />
      <PaymentConsent checked={hasConsented} onChange={setHasConsented} />
      <PaymentButton orderId={order.id} callbackUrl={callbackUrl} disabled={!hasConsented} />
    </div>
  );
}
