import { useParams } from "react-router-dom";
import { useOrder } from "@/hooks/use-order";
import { TrackingPage } from "@/components/tracking/TrackingPage";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function TrackOrder() {
  const { orderId } = useParams<{ orderId: string }>();
  const { order, isLoading } = useOrder(orderId);

  if (isLoading || !order) return <LoadingScreen label="Loading tracking…" />;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 font-display text-xl text-ink">Tracking — {order.order_number}</h1>
      <TrackingPage order={order} />
    </div>
  );
}
