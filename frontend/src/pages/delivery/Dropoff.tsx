import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";
import { deliveryRoutes } from "@/config/routes.config";

export default function Dropoff() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmDelivery() {
    if (!deliveryId) return;
    setBusy(true);
    setError(null);
    try {
      await deliveriesApi.markDelivered(deliveryId);
      navigate(deliveryRoutes.details(deliveryId));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm">
      <h1 className="mb-4 font-display text-xl text-ink">Confirm drop-off</h1>
      <p className="mb-4 text-sm text-ink-soft">
        Confirm only after handing over the package. Photo proof upload is not enabled in this version.
      </p>
      <Button isLoading={busy} onClick={() => void confirmDelivery()}>Confirm delivered</Button>
      {error && <p role="alert" className="mt-3 text-sm text-thread">{error}</p>}
    </div>
  );
}
