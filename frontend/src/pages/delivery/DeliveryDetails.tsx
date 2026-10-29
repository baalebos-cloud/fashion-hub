import { useState } from "react";
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
  const { delivery, isLoading, error } = useDelivery(deliveryId);

  if (error) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !delivery) return <LoadingScreen label="Loading delivery…" />;

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Order {delivery.order_id.slice(0, 8)}</h1>
        <DeliveryStatusBadge status={delivery.status} />
      </div>
      {["assigned", "picked_up", "in_transit", "out_for_delivery"].includes(delivery.status) && (
        <Button variant="secondary" onClick={() => setShowIssue(true)}>Report Issue</Button>
      )}
      {showIssue && <ReportIssueModal deliveryId={delivery.id} onClose={() => setShowIssue(false)} />}
      <div className="text-lg font-medium text-ink">{formatCurrency(delivery.delivery_fee)}</div>
      {delivery.status === "assigned" && (
        <Button className="self-start" onClick={() => navigate(deliveryRoutes.pickup(delivery.id))}>
          Confirm pickup
        </Button>
      )}
      {["in_transit", "picked_up", "out_for_delivery"].includes(delivery.status) && (
        <Button className="self-start" onClick={() => navigate(deliveryRoutes.dropoff(delivery.id))}>
          Confirm drop-off
        </Button>
      )}
    </div>
  );
}
