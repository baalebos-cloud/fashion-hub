import { useState } from "react";
import { DeliveryRequest, type DeliveryRequestData } from "@/components/delivery/DeliveryRequest";
import { EmptyState } from "@/components/ui/empty-state";

/** Broadcasted requests arrive via
 * DeliveryRequestService.broadcast_to_nearby_partners on the backend
 * (currently a documented stub — see backend/docs/delivery.md); this page
 * is ready to render them via a WebSocket/poll once that's implemented. */
export default function DeliveryRequests() {
  const [requests] = useState<DeliveryRequestData[]>([]);

  if (requests.length === 0) {
    return <EmptyState title="No delivery requests right now" description="New requests near you will appear here." />;
  }

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">Delivery requests</h1>
      {requests.map((request) => (
        <DeliveryRequest key={request.id} request={request} onAccept={async () => {}} onReject={async () => {}} />
      ))}
    </div>
  );
}
