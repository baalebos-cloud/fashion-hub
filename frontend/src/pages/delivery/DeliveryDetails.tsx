import { useParams } from "react-router-dom";
import { useDelivery } from "@/hooks/use-delivery";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { formatCurrency } from "@/lib/formatters/currency";

export default function DeliveryDetails() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading } = useDelivery(deliveryId);

  if (isLoading || !delivery) return <LoadingScreen label="Loading delivery…" />;

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl text-ink">Order {delivery.order_id.slice(0, 8)}</h1>
        <DeliveryStatusBadge status={delivery.status} />
      </div>
      <div className="text-lg font-medium text-ink">{formatCurrency(delivery.delivery_fee)}</div>
    </div>
  );
}
