import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { OrderItems } from "@/components/orders/OrderItems";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { PaymentButton } from "@/components/payments/PaymentButton";
import { PaymentConsent } from "@/components/payments/PaymentConsent";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { professionalRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";

export default function VendorOrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, error, cancel } = useOrder(orderId);
  const [hasConsented, setHasConsented] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [isCancelling, setIsCancelling] = useState(false);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  if (error && !order) return <p role="alert">{error}</p>;
  if (isLoading || !order) return <LoadingScreen label="Loading order…" />;
  if (order.order_type !== "vendor_order") return <p role="alert">This is not a material order.</p>;
  const unpaid = order.status === "checkout" || order.status === "payment_pending";
  const expired = !order.reservation_expires_at || Date.parse(order.reservation_expires_at) <= now;
  async function cancelOrder() {
    setIsCancelling(true);
    try { await cancel("Cancelled by material buyer."); }
    catch { /* The order store displays the error. */ }
    finally { setIsCancelling(false); }
  }
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <h1 className="font-display text-xl text-ink">{order.order_number}</h1>
      <p>Status: {order.status.replaceAll("_", " ")}</p>
      <OrderItems items={order.items} currency={order.currency} />
      <p className="text-lg font-medium">Final total: {formatCurrency(order.total_amount, order.currency)}</p>
      {unpaid && <>
        {order.reservation_expires_at && <p>Stock hold ends: <DateTimeDisplay value={order.reservation_expires_at} /></p>}
        {expired ? <p role="status">The stock hold has expired. Create a new order from the marketplace; check any payment already made before paying again.</p> : <>
          <PaymentConsent checked={hasConsented} onChange={setHasConsented} />
          <PaymentButton key={order.id} orderId={order.id} callbackUrl={`${window.location.origin}${professionalRoutes.vendorPaymentSuccess}`} disabled={!hasConsented || isCancelling} />
        </>}
        <Button variant="secondary" onClick={() => { void cancelOrder(); }} isLoading={isCancelling}>Cancel unpaid order</Button>
      </>}
      {error && <p role="alert">{error}</p>}
      <OrderTimeline entries={timeline} />
      <Link to={professionalRoutes.vendorOrders} className="underline">View material orders</Link>
      <Link to={professionalRoutes.vendorMarketplace} className="underline">Continue shopping</Link>
    </div>
  );
}
