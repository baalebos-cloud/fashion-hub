import { useParams, useNavigate } from "react-router-dom";
import { useRef, useState } from "react";
import { useDelivery } from "@/hooks/use-delivery";
import { deliveriesApi, newIdempotencyKey } from "@/api/deliveries.api";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { deliveryRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { isApiError } from "@/lib/api/errors";
import { CodeEntry, codeOutcome } from "@/components/delivery/CodeEntry";

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
  const [wrongCount, setWrongCount] = useState(0);
  const [locked, setLocked] = useState(false);
  const [wrongMessage, setWrongMessage] = useState<string | null>(null);
  // Same key for retries of this one confirmation.
  const attemptKey = useRef("");
  if (!attemptKey.current) attemptKey.current = newIdempotencyKey();

  if (error) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !delivery) return <LoadingScreen label="Loading delivery…" />;
  const codeRequired = delivery.pickup_code_required !== false;

  async function handleConfirm() {
    if (!deliveryId) return;
    setActionError(null);
    setIsConfirming(true);
    try {
      await deliveriesApi.markPickedUp(deliveryId, codeRequired ? { pickup_code: pickupCode, package_count: packageCount } : { package_count: packageCount }, attemptKey.current);
      navigate(deliveryRoutes.navigation(deliveryId));
    } catch (err) {
      // A definite rejection (wrong code, wrong state) starts a new attempt; a dropped
      // connection or server error keeps the key so the retry can't apply twice.
      if (isApiError(err) && err.status != null && err.status >= 400 && err.status < 500) attemptKey.current = newIdempotencyKey();
      const outcome = codeOutcome(err);
      if (codeRequired && outcome.kind === "wrong") { setWrongCount((n) => n + 1); setWrongMessage(outcome.message); setPickupCode(""); }
      else if (codeRequired && outcome.kind === "locked") setLocked(true);
      else setActionError(outcome.message || getDisplayErrorMessage(err));
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 pb-28 md:pb-0">
      <h1 className="font-display text-3xl text-ink">Confirm pickup</h1>
      <section className="flex flex-col gap-4 rounded-card border border-line bg-surface p-5">
        {codeRequired && (
          <CodeEntry id="pickup-code" label="Pickup code" value={pickupCode} onChange={setPickupCode}
            hint="Ask the seller to read out their 6-digit pickup code."
            wrongCount={wrongCount} locked={locked} message={wrongMessage} />
        )}
        <div className="flex flex-col gap-2">
          <p id="package-count-label" className="text-sm font-semibold text-ink">Packages collected</p>
          <div className="flex items-center gap-3" role="group" aria-labelledby="package-count-label">
            <Button type="button" variant="secondary" aria-label="Fewer packages" disabled={packageCount <= 1}
              className="w-12 px-0 text-lg" onClick={() => setPackageCount((n) => Math.max(1, n - 1))}>−</Button>
            <span className="w-10 text-center font-mono text-2xl font-medium text-ink" aria-live="polite" data-testid="package-count">{packageCount}</span>
            <Button type="button" variant="secondary" aria-label="More packages" disabled={packageCount >= 50}
              className="w-12 px-0 text-lg" onClick={() => setPackageCount((n) => Math.min(50, n + 1))}>+</Button>
          </div>
        </div>
        <p className="text-[13px] text-ink-soft">Check the order number on the package matches before you leave.</p>
      </section>
      {actionError && <p role="alert" className="text-sm text-thread">{actionError}</p>}
      <div className="bottom-action-bar fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface p-4 pb-[max(1rem,env(safe-area-inset-bottom))] md:static md:border-0 md:bg-transparent md:p-0">
        <Button size="lg" className="w-full" onClick={() => void handleConfirm()} isLoading={isConfirming}
          disabled={isConfirming || locked || (codeRequired && pickupCode.length !== 6)}>I've picked up the package</Button>
      </div>
    </div>
  );
}
