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
  const [handoverCode, setHandoverCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function confirmDelivery() {
    if (!deliveryId) return;
    setBusy(true);
    setError(null);
    try {
      await deliveriesApi.markDelivered(deliveryId, handoverCode);
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
      <label className="mb-3 block text-sm">Customer handover code
        <input aria-label="Customer handover code" value={handoverCode} inputMode="numeric"
          className="mt-2 w-full rounded border border-line p-3"
          onChange={(event) => setHandoverCode(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
          maxLength={6} placeholder="6-digit code" autoComplete="one-time-code" />
      </label>
      <p className="mb-3 text-xs text-ink-soft">Ask the customer for their code only after handing over the package.</p>
      <Button isLoading={busy} disabled={busy || handoverCode.length !== 6} onClick={() => void confirmDelivery()}>Confirm delivered</Button>
      {error && <p role="alert" className="mt-3 text-sm text-thread">{error}</p>}
    </div>
  );
}
