import { useEffect, useState } from "react";
import { describeRoute } from "@/lib/utils/route";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { Button } from "@/components/ui/button";
import { formatNaira } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Delivery } from "@/types/delivery";
import type { ReservedJob } from "@/types/dispatch";

const REFRESH_MS = 10_000;

function secondsLeft(expiresAt: string, now: number) {
  return Math.max(0, Math.round((Date.parse(expiresAt) - now) / 1000));
}

/**
 * Jobs Tailora reserved for this rider (auto-dispatch). Each has a short exclusive
 * window; accepting assigns it, declining passes it to the next rider. Renders
 * nothing when auto-offers are off or nothing is reserved.
 */
export function ReservedJobs({ onAccepted, onChanged }: { onAccepted: (delivery: Delivery) => void; onChanged?: () => void }) {
  const [jobs, setJobs] = useState<ReservedJob[]>([]);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    deliveryRequestsApi.reservedForMe().then((data) => { if (active) setJobs(Array.isArray(data) ? data : []); })
      .catch(() => { if (active) setJobs([]); });
    const timer = window.setTimeout(() => setTick((t) => t + 1), REFRESH_MS);
    return () => { active = false; window.clearTimeout(timer); };
  }, [tick]);

  useEffect(() => {
    if (jobs.length === 0) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [jobs.length]);

  const live = jobs.filter((j) => secondsLeft(j.expires_at, now) > 0);
  if (live.length === 0) return null;

  async function act(offerId: string, accept: boolean) {
    setBusy(offerId);
    setError(null);
    try {
      if (accept) onAccepted(await deliveryRequestsApi.acceptReserved(offerId));
      else { await deliveryRequestsApi.declineReserved(offerId); onChanged?.(); }
    } catch (err) {
      setError(getDisplayErrorMessage(err, "That didn't work. The offer may have expired."));
    } finally {
      setBusy(null);
      setTick((t) => t + 1);
    }
  }

  return (
    <section aria-label="Reserved for you" className="flex flex-col gap-3">
      {live.map((reserved) => {
        const left = secondsLeft(reserved.expires_at, now);
        return (
          <div key={reserved.id} className="rounded-card border-2 border-brass bg-[#fbf6ec] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-brass-deep">Reserved for you</p>
                <p className="mt-1 font-display text-2xl text-ink">{formatNaira(reserved.job.suggested_fare)}</p>
                <p className="text-xs text-ink-soft">
                  {describeRoute(reserved.job.route, reserved.job.approx_road_km) && `${describeRoute(reserved.job.route, reserved.job.approx_road_km)} · `}
                  {reserved.job.pickup_area ?? "Pickup area"} → {reserved.job.dropoff_area ?? "Drop-off area"}
                </p>
              </div>
              <span role="timer" aria-live="off" className="rounded-full bg-ink px-2.5 py-1 text-sm font-medium tabular-nums text-paper">
                {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}
              </span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Button size="sm" onClick={() => void act(reserved.id, true)} isLoading={busy === reserved.id} disabled={busy !== null}>
                Accept {formatNaira(reserved.job.suggested_fare)}
              </Button>
              <Button size="sm" variant="secondary" onClick={() => void act(reserved.id, false)} disabled={busy !== null}>
                Decline
              </Button>
            </div>
          </div>
        );
      })}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </section>
  );
}
