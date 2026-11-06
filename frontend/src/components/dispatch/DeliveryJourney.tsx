import { useEffect, useState } from "react";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { Card } from "@/components/ui/card";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { describeFreshness } from "@/lib/utils/tracking";
import type { DeliveryJourney as Journey } from "@/types/dispatch";

const REFRESH_MS = 20_000;

/** Logistics-style step tracker with times, plus an approximate live ETA while in transit. */
export function DeliveryJourney({ orderId }: { orderId: string }) {
  const [journey, setJourney] = useState<Journey | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    deliveryRequestsApi.journey(orderId)
      .then((data) => { if (active) setJourney(Array.isArray(data?.milestones) ? data : null); })
      .catch(() => {});
    const timer = window.setTimeout(() => setTick((t) => t + 1), REFRESH_MS);
    return () => { active = false; window.clearTimeout(timer); };
  }, [orderId, tick]);

  if (!journey) return null;
  const { live } = journey;

  return (
    <Card role="region" aria-label="Delivery journey" className="p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-lg text-ink">Delivery journey</h2>
        <span className="text-xs text-ink-soft">Tracking no. <span className="font-medium text-ink">{journey.tracking_number}</span></span>
      </div>

      {live?.eta_minutes != null && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-ink px-4 py-3 text-paper" role="status">
          <div>
            <p className="text-xs text-paper/70">Arriving in about</p>
            <p className="font-display text-2xl">{live.eta_minutes} min</p>
          </div>
          {live.distance_remaining_km != null && (
            <p className="text-right text-xs text-paper/80">≈ {live.distance_remaining_km.toFixed(1)} km away<br />
              <span className="text-paper/60">{live.basis === "road_route"
                ? `Road route from the rider's live location${live.traffic_aware ? ", with traffic" : ""}`
                : "Estimate from the rider's live location"}</span></p>
          )}
        </div>
      )}

      {journey.tracking && journey.tracking.state !== "live" && journey.tracking.state !== "delayed" && (
        <p className="mt-3 rounded-lg bg-muslin px-3 py-2 text-xs text-ink-soft" role="status" data-testid="journey-tracking">
          {describeFreshness(journey.tracking.state, journey.tracking.age_seconds).label}.
        </p>
      )}

      <ol className="mt-4">
        {journey.milestones.map((step, index) => {
          const last = index === journey.milestones.length - 1;
          return (
            <li key={step.key} className="relative flex gap-3 pb-4 last:pb-0" aria-current={step.state === "current" ? "step" : undefined}>
              {!last && <span aria-hidden="true" className={`absolute left-[7px] top-4 h-full w-0.5 ${step.state === "done" ? "bg-brass" : "bg-line"}`} />}
              <span aria-hidden="true" className={
                step.state === "done" ? "relative mt-0.5 h-4 w-4 shrink-0 rounded-full bg-brass"
                  : step.state === "current" ? "relative mt-0.5 h-4 w-4 shrink-0 rounded-full border-4 border-brass bg-paper"
                    : "relative mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 border-line bg-paper"} />
              <div className="min-w-0">
                <p className={step.state === "upcoming" ? "text-sm text-ink-soft" : "text-sm font-medium text-ink"}>
                  {step.label}
                  {step.state === "current" && <span className="sr-only"> (current step)</span>}
                </p>
                {step.at && <p className="text-xs text-ink-soft"><DateTimeDisplay value={step.at} /></p>}
              </div>
            </li>
          );
        })}
      </ol>

      {journey.materials_legs && journey.materials_legs.length > 0 && (
        <div className="mt-4 border-t border-line pt-3" role="region" aria-label="Materials for this order">
          <h3 className="text-sm font-medium text-ink">Materials for this order</h3>
          <ul className="mt-2 flex flex-col gap-2">
            {journey.materials_legs.map((leg) => (
              <li key={leg.order_id} className="flex items-start gap-2 text-sm">
                <span aria-hidden="true" className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${leg.done ? "bg-brass" : "border border-brass"}`} />
                <div>
                  <p className="text-ink">{leg.label}</p>
                  <p className="text-xs text-ink-soft">
                    From {leg.vendor_name}{leg.updated_at && <> · <DateTimeDisplay value={leg.updated_at} format="relative" /></>}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
