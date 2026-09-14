import { useTracking } from "@/hooks/use-tracking";
import { TrackingMap } from "./TrackingMap";
import { TrackingTimeline } from "./TrackingTimeline";
import { DeliveryStatus } from "./DeliveryStatus";
import { EstimatedDelivery } from "./EstimatedDelivery";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import type { Order } from "@/types/order";

export function TrackingPage({ order }: { order: Order }) {
  const isActive = !["delivered", "received", "completed", "cancelled"].includes(order.status);
  const { tracking } = useTracking(order.id, isActive);

  if (!tracking) return <LoadingScreen label="Fetching the latest tracking update…" />;

  return (
    <div className="flex flex-col gap-6">
      <TrackingMap tracking={tracking.tracking} />
      <div className="flex items-center justify-between">
        <DeliveryStatus status={tracking.status} />
        {tracking.tracking?.eta_minutes != null && <EstimatedDelivery etaMinutes={tracking.tracking.eta_minutes} />}
      </div>
      <TrackingTimeline orderId={order.id} />
    </div>
  );
}
