import { useEffect, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import type { DeliveryTrip } from "@/types/delivery";
import { DispatchTripCard } from "@/components/delivery/DispatchTripCard";
import { ReportIssueModal } from "@/components/delivery/ReportIssueModal";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { deliveryRoutes } from "@/config/routes.config";
import { useDelivery } from "@/hooks/use-delivery";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { formatCurrency } from "@/lib/formatters/currency";

export default function DeliveryDetails() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const navigate = useNavigate();
  const [showIssue, setShowIssue] = useState(false);
  const [trip, setTrip] = useState<DeliveryTrip | null>(null);
  useEffect(() => {
    if (!deliveryId) return;
    let active = true;
    deliveriesApi.getTrip(deliveryId).then(data => { if (active) setTrip(data); }).catch(() => {});
    return () => { active = false; };
  }, [deliveryId]);
  const { delivery, isLoading, error } = useDelivery(deliveryId);

  if (error) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !delivery) return <LoadingScreen label="Loading delivery…" />;

  const active = ["assigned", "picked_up", "in_transit", "out_for_delivery"].includes(delivery.status);
  const toDropoff = ["in_transit", "picked_up", "out_for_delivery"].includes(delivery.status);
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 pb-28 md:pb-0">
      <header className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <DeliveryStatusBadge status={delivery.status} />
          <span className="font-mono text-sm text-ink-soft">Order {delivery.order_id.slice(0, 8).toUpperCase()}</span>
        </div>
        <h1 className="font-display text-3xl text-ink">{delivery.status === "assigned" ? "Go to pickup" : toDropoff ? "Deliver to customer" : "Delivery"}</h1>
        <p className="text-sm text-ink-soft">Fare <span className="font-mono font-semibold text-ink">{formatCurrency(delivery.delivery_fee)}</span></p>
      </header>
      {trip && <DispatchTripCard trip={trip} />}
      {active && (
        <Button variant="danger" className="self-start" onClick={() => setShowIssue(true)}>Report a problem</Button>
      )}
      {showIssue && <ReportIssueModal deliveryId={delivery.id} onClose={() => setShowIssue(false)} />}
      {(delivery.status === "assigned" || toDropoff) && (
        <div className="bottom-action-bar fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface p-4 pb-[max(1rem,env(safe-area-inset-bottom))] md:static md:border-0 md:bg-transparent md:p-0">
          {delivery.status === "assigned" ? (
            <Button size="lg" className="w-full" onClick={() => navigate(deliveryRoutes.pickup(delivery.id))}>Confirm pickup</Button>
          ) : (
            <Button size="lg" className="w-full" onClick={() => navigate(deliveryRoutes.dropoff(delivery.id))}>Confirm drop-off</Button>
          )}
        </div>
      )}
    </div>
  );
}
