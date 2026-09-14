import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/formatters/currency";

export interface DeliveryRequestData {
  id: string;
  pickupLabel: string;
  dropoffLabel: string;
  proposedFee: number | null;
}

export function DeliveryRequest({ request, onAccept, onReject }: { request: DeliveryRequestData; onAccept: () => Promise<void>; onReject: (reason: string) => Promise<void> }) {
  const [isAccepting, setIsAccepting] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  return (
    <Card className="flex flex-col gap-2">
      <div className="text-sm text-ink">{request.pickupLabel} → {request.dropoffLabel}</div>
      {request.proposedFee != null && <div className="text-sm font-medium text-ink">{formatCurrency(request.proposedFee)}</div>}
      <div className="flex gap-2">
        <Button
          size="sm"
          isLoading={isAccepting}
          onClick={async () => { setIsAccepting(true); try { await onAccept(); } finally { setIsAccepting(false); } }}
        >
          Accept
        </Button>
        <Button
          size="sm"
          variant="secondary"
          isLoading={isRejecting}
          onClick={async () => { setIsRejecting(true); try { await onReject("Not available"); } finally { setIsRejecting(false); } }}
        >
          Decline
        </Button>
      </div>
    </Card>
  );
}
