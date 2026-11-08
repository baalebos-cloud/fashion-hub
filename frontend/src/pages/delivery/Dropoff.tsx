import { useParams, useNavigate } from "react-router-dom";
import { useRef, useState } from "react";
import { deliveriesApi, newIdempotencyKey } from "@/api/deliveries.api";
import { useDelivery } from "@/hooks/use-delivery";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { isApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { deliveryRoutes } from "@/config/routes.config";
import { CodeEntry, codeOutcome } from "@/components/delivery/CodeEntry";
import { OrderContacts } from "@/components/calls/OrderContacts";

export default function Dropoff() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [handoverCode, setHandoverCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [wrongCount, setWrongCount] = useState(0);
  const [locked, setLocked] = useState(false);
  const [wrongMessage, setWrongMessage] = useState<string | null>(null);
  const { delivery } = useDelivery(deliveryId);
  const attemptKey = useRef("");
  if (!attemptKey.current) attemptKey.current = newIdempotencyKey();

  async function confirmDelivery() {
    if (!deliveryId) return;
    setBusy(true);
    setError(null);
    try {
      await deliveriesApi.markDelivered(deliveryId, handoverCode, attemptKey.current);
      navigate(deliveryRoutes.details(deliveryId));
    } catch (err) {
      // A definite rejection (wrong code, wrong state) starts a new attempt; a dropped
      // connection or server error keeps the key so the retry can't apply twice.
      if (isApiError(err) && err.status != null && err.status >= 400 && err.status < 500) attemptKey.current = newIdempotencyKey();
      const outcome = codeOutcome(err);
      if (outcome.kind === "wrong") { setWrongCount((n) => n + 1); setWrongMessage(outcome.message); setHandoverCode(""); }
      else if (outcome.kind === "locked") setLocked(true);
      else setError(outcome.message || getDisplayErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 pb-28 md:pb-0">
      <h1 className="font-display text-3xl text-ink">Confirm drop-off</h1>
      {delivery?.package_count != null && (
        <p className="rounded-control bg-warning-wash px-3 py-2 text-sm text-warning">
          Hand over all {delivery.package_count} package{delivery.package_count === 1 ? "" : "s"} you collected.
        </p>
      )}
      <section className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
        <CodeEntry id="handover-code" label="Customer handover code" value={handoverCode} onChange={setHandoverCode}
          hint="Hand over the package first, then ask the customer for their 6-digit code. If it has expired, they can open a fresh one in the app."
          wrongCount={wrongCount} locked={locked} message={wrongMessage} />
        <p className="text-[13px] text-ink-soft">Photo proof upload isn't switched on in this version.</p>
      </section>
      {delivery?.order_id && <OrderContacts orderId={delivery.order_id} />}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <div className="bottom-action-bar fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface p-4 pb-[max(1rem,env(safe-area-inset-bottom))] md:static md:border-0 md:bg-transparent md:p-0">
        <Button size="lg" className="w-full" isLoading={busy} disabled={busy || locked || handoverCode.length !== 6}
          onClick={() => void confirmDelivery()}>Confirm delivered</Button>
      </div>
    </div>
  );
}
