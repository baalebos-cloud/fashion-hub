import { useState } from "react";
import { Link } from "react-router-dom";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { DispatchOffers } from "./DispatchOffers";

/**
 * Seller's "request a rider" step for an order that's ready for pickup, followed by the
 * live offers panel. Used for materials orders (vendor -> tailor).
 */
export function RequestRiderPanel({ orderId, pickupSettingsPath }: { orderId: string; pickupSettingsPath: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);

  async function request() {
    setBusy(true);
    setError(null);
    try {
      await deliveryRequestsApi.requestForOrder(orderId);
      setRefresh((n) => n + 1);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't request a rider."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Card className="flex flex-col gap-2 p-4">
        <h2 className="text-sm font-medium text-ink">Delivery to the tailor</h2>
        <p className="text-xs text-ink-soft">
          Request a rider and nearby riders can accept at the suggested fare or send you an offer.
          The tailor gets a handover code to confirm delivery.
        </p>
        <Button className="self-start" onClick={() => void request()} isLoading={busy}>Request a rider</Button>
        {error && (
          <p role="alert" className="text-sm text-thread">
            {error}{" "}
            {/pickup location/i.test(error) && <Link to={pickupSettingsPath} className="font-medium underline">Set pickup location</Link>}
          </p>
        )}
      </Card>
      <DispatchOffers orderId={orderId} refreshKey={refresh} onAssigned={() => setRefresh((n) => n + 1)} />
    </div>
  );
}
