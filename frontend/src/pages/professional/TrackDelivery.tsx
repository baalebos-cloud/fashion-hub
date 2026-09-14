import { useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { TrackingPage } from "@/components/tracking/TrackingPage";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function TrackDelivery() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { order, isLoading } = useOrder(deliveryId);

  if (isLoading || !order) return <LoadingScreen label="Loading tracking…" />;

  return <TrackingPage order={order} />;
}
