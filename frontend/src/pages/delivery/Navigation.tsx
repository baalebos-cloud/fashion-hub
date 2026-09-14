import { useParams } from "react-router-dom";
import { useDelivery } from "@/hooks/use-delivery";
import { DeliveryMap } from "@/components/delivery/DeliveryMap";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Navigation() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading } = useDelivery(deliveryId);

  if (isLoading || !delivery) return <LoadingScreen />;

  return (
    <div>
      <h1 className="mb-4 font-display text-xl text-ink">Navigate</h1>
      <DeliveryMap />
    </div>
  );
}
