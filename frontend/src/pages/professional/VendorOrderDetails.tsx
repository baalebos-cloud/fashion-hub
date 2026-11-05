import { useEffect, useState } from "react";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { DeliveryJourney } from "@/components/dispatch/DeliveryJourney";
import { CustomerDeliveryTracking } from "@/components/delivery/CustomerDeliveryTracking";
import { ordersApi } from "@/api/orders.api";
import { Link, useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { OrderItems } from "@/components/orders/OrderItems";
import { OrderTimeline } from "@/components/orders/OrderTimeline";
import { InterswitchSandboxButton } from "@/components/payments/InterswitchSandboxButton";
import { InterswitchLiveButton } from "@/components/payments/InterswitchLiveButton";
import { PaymentButton } from "@/components/payments/PaymentButton";
import { PaymentConsent } from "@/components/payments/PaymentConsent";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { professionalRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export default function VendorOrderDetails() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, timeline, isLoading, error, cancel } = useOrder(orderId);
  const [hasConsented, setHasConsented] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [isCancelling, setIsCancelling] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [receivedStatus, setReceivedStatus] = useState<string | null>(null);
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
    setIsCancelling(true); setActionError(null);
    try { await cancel("Cancelled by material buyer."); }
    catch (err) { setActionError(getDisplayErrorMessage(err)); }
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
          {import.meta.env.VITE_INTERSWITCH_LIVE_UI_ENABLED === "true" ? (
            <InterswitchLiveButton orderId={order.id} disabled={!hasConsented || isCancelling} />
          ) : (
            <PaymentButton key={order.id} orderId={order.id} callbackUrl={`${window.location.origin}${professionalRoutes.vendorPaymentSuccess}`} disabled={!hasConsented || isCancelling} />
          )}
          {import.meta.env.VITE_INTERSWITCH_LIVE_UI_ENABLED !== "true" && import.meta.env.VITE_INTERSWITCH_SANDBOX_UI_ENABLED === "true" && (
            <InterswitchSandboxButton orderId={order.id} disabled={!hasConsented || isCancelling} />
          )}
        </>}
        <Button variant="secondary" onClick={() => { void cancelOrder(); }} isLoading={isCancelling}>Cancel unpaid order</Button>
      </>}
      {!unpaid && ["ready_for_pickup", "picked_up", "in_transit", "delivered", "received", "completed"].includes(order.status) && (
        <DeliveryJourney orderId={order.id} />
      )}
      {!unpaid && <CustomerDeliveryTracking orderId={order.id} />}
      {(receivedStatus ?? order.status) === "delivered" && (
        <div className="flex flex-col gap-2 rounded-card border border-line p-4">
          <p className="text-sm text-ink">Check the materials, then confirm you received them. This completes the materials order.</p>
          <Button className="self-start" isLoading={confirming} onClick={async () => {
            setConfirming(true); setActionError(null);
            try { setReceivedStatus((await ordersApi.confirmMaterialsReceived(order.id)).status); }
            catch (err) { setActionError(getDisplayErrorMessage(err)); }
            finally { setConfirming(false); }
          }}>Confirm materials received</Button>
        </div>
      )}
      {receivedStatus === "completed" && <p role="status" className="text-sm text-[#256a3f]">Materials received. Thank you!</p>}
      {!unpaid && <OrderContacts orderId={order.id} />}
      {error && <p role="alert">{error}</p>}
      {actionError && <p role="alert">{actionError}</p>}
      <OrderTimeline entries={timeline} />
      <Link to={professionalRoutes.vendorOrders} className="underline">View material orders</Link>
      <Link to={professionalRoutes.vendorMarketplace} className="underline">Continue shopping</Link>
    </div>
  );
}
