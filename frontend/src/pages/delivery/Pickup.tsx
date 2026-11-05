import { useParams, useNavigate } from "react-router-dom";
import { useRef, useState } from "react";
import { useDelivery } from "@/hooks/use-delivery";
import { deliveriesApi, newIdempotencyKey } from "@/api/deliveries.api";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { deliveryRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { isApiError } from "@/lib/api/errors";

/**
 * Rider confirms collection: the seller reads out a one-time pickup code, and the rider
 * records how many packages they took so the recipient can check at the door.
 */
export default function Pickup() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading, error } = useDelivery(deliveryId);
  const navigate = useNavigate();
  const [pickupCode, setPickupCode] = useState("");
  const [packageCount, setPackageCount] = useState(1);
  const [isConfirming, setIsConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  // Same key for retries of this one confirmation.
  const attemptKey = useRef("");
  if (!attemptKey.current) attemptKey.current = newIdempotencyKey();

  if (error) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !delivery) return <LoadingScreen label="Loading delivery…" />;

  async function handleConfirm() {
    if (!deliveryId) return;
    setActionError(null);
    setIsConfirming(true);
    try {
      await deliveriesApi.markPickedUp(deliveryId, { pickup_code: pickupCode, package_count: packageCount }, attemptKey.current);
      navigate(deliveryRoutes.navigation(deliveryId));
    } catch (err) {
      // A definite rejection (wrong code, wrong state) starts a new attempt; a dropped
      // connection or server error keeps the key so the retry can't apply twice.
      if (isApiError(err) && err.status != null && err.status >= 400 && err.status < 500) attemptKey.current = newIdempotencyKey();
      setActionError(getDisplayErrorMessage(err));
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Confirm pickup</h1>
      <label className="block text-sm text-ink">Pickup code from the seller
        <input aria-label="Pickup code" value={pickupCode} inputMode="numeric" autoComplete="one-time-code"
          className="mt-2 w-full rounded border border-line p-3 tracking-widest"
          onChange={(event) => setPickupCode(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
          maxLength={6} placeholder="6-digit code" />
      </label>
      <div className="text-sm text-ink">
        <p id="package-count-label">Packages collected</p>
        <div className="mt-2 flex items-center gap-3" role="group" aria-labelledby="package-count-label">
          <button type="button" aria-label="Fewer packages" disabled={packageCount <= 1}
            onClick={() => setPackageCount((n) => Math.max(1, n - 1))}
            className="h-10 w-10 rounded border border-line text-lg disabled:opacity-40">−</button>
          <span className="w-8 text-center text-lg font-medium" aria-live="polite" data-testid="package-count">{packageCount}</span>
          <button type="button" aria-label="More packages" disabled={packageCount >= 50}
            onClick={() => setPackageCount((n) => Math.min(50, n + 1))}
            className="h-10 w-10 rounded border border-line text-lg disabled:opacity-40">+</button>
        </div>
      </div>
      <p className="text-xs text-ink-soft">Check the order number on the package matches before you leave.</p>
      <Button onClick={() => void handleConfirm()} isLoading={isConfirming}
        disabled={isConfirming || pickupCode.length !== 6}>I've picked up the package</Button>
      {actionError && <p role="alert" className="text-sm text-thread">{actionError}</p>}
    </div>
  );
}
