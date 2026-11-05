import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { trackingLinksApi, type PublicTracking as Tracking } from "@/api/tracking-links.api";
import { Card } from "@/components/ui/card";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { publicRoutes } from "@/config/routes.config";

const REFRESH_MS = 30_000;
const VEHICLE: Record<string, string> = { bike: "Motorbike", car: "Car", van: "Van", foot: "On foot" };

/**
 * Account-free tracking page opened from a link the buyer shared. Shows only what a
 * recipient needs: progress, rider first name and vehicle, ETA estimate, drop-off area.
 */
export default function PublicTracking() {
  const { token = "" } = useParams<{ token: string }>();
  const [tracking, setTracking] = useState<Tracking | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    // Private, per-delivery page: keep it out of search engines and referrers.
    const robots = document.createElement("meta");
    robots.name = "robots";
    robots.content = "noindex, nofollow";
    const referrer = document.createElement("meta");
    referrer.name = "referrer";
    referrer.content = "no-referrer";
    document.head.append(robots, referrer);
    return () => { robots.remove(); referrer.remove(); };
  }, []);

  useEffect(() => {
    let active = true;
    trackingLinksApi.publicView(token)
      .then((data) => { if (active) { setTracking(data); setState("ready"); document.title = `Tracking ${data.tracking_number} · Tailora`; } })
      .catch(() => { if (active) setState((current) => (current === "ready" ? current : "missing")); });
    const timer = window.setTimeout(() => setTick((t) => t + 1), REFRESH_MS);
    return () => { active = false; window.clearTimeout(timer); };
  }, [token, tick]);

  if (state === "loading") return <p role="status" className="mx-auto max-w-lg px-4 py-16 text-center text-sm text-ink-soft">Loading delivery…</p>;
  if (state === "missing" || !tracking) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <h1 className="font-display text-2xl text-ink">This tracking link isn't available</h1>
        <p className="mt-2 text-sm text-ink-soft">It may have expired, been switched off by the sender, or the delivery is complete.</p>
        <Link to={publicRoutes.home} className="mt-6 inline-block text-sm font-medium text-brass-deep underline">Go to Tailora</Link>
      </div>
    );
  }

  const delivered = ["delivered", "received", "completed"].includes(tracking.status);
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-4 px-4 py-8">
      <div>
        <p className="text-xs uppercase tracking-wide text-ink-soft">
          {tracking.kind === "materials" ? "Materials delivery" : "Delivery"} from {tracking.seller_name}
        </p>
        <h1 className="font-display text-2xl text-ink">{delivered ? "Delivered" : "On its way"}</h1>
        <p className="text-sm text-ink-soft">
          Tracking no. <span className="font-medium text-ink">{tracking.tracking_number}</span>
          {tracking.dropoff_area && <> · to {tracking.dropoff_area}</>}
        </p>
      </div>

      {tracking.eta_minutes != null && !delivered && (
        <div className="rounded-card bg-ink px-4 py-3 text-paper" role="status">
          <p className="text-xs text-paper/70">Arriving in about</p>
          <p className="font-display text-3xl">{tracking.eta_minutes} min</p>
          <p className="text-xs text-paper/60">Estimate from the rider's live location</p>
        </div>
      )}

      {tracking.rider && (
        <Card className="flex items-center justify-between gap-3 p-4">
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-ink">{tracking.rider.first_name}</span>
              {tracking.rider.is_verified && <VerificationBadge />}
            </div>
            <p className="text-xs text-ink-soft">
              {[tracking.rider.vehicle_type ? VEHICLE[tracking.rider.vehicle_type] ?? tracking.rider.vehicle_type : null,
                tracking.rider.rating > 0 ? `★ ${tracking.rider.rating.toFixed(1)}` : null].filter(Boolean).join(" · ") || "Your rider"}
            </p>
          </div>
        </Card>
      )}

      <Card className="p-4" role="region" aria-label="Delivery progress">
        <ol>
          {tracking.milestones.map((step, index) => {
            const last = index === tracking.milestones.length - 1;
            return (
              <li key={step.key} className="relative flex gap-3 pb-4 last:pb-0" aria-current={step.state === "current" ? "step" : undefined}>
                {!last && <span aria-hidden="true" className={`absolute left-[7px] top-4 h-full w-0.5 ${step.state === "done" ? "bg-brass" : "bg-line"}`} />}
                <span aria-hidden="true" className={step.state === "done" ? "relative mt-0.5 h-4 w-4 shrink-0 rounded-full bg-brass"
                  : step.state === "current" ? "relative mt-0.5 h-4 w-4 shrink-0 rounded-full border-4 border-brass bg-paper"
                    : "relative mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 border-line bg-paper"} />
                <div>
                  <p className={step.state === "upcoming" ? "text-sm text-ink-soft" : "text-sm font-medium text-ink"}>{step.label}</p>
                  {step.at && <p className="text-xs text-ink-soft"><DateTimeDisplay value={step.at} /></p>}
                </div>
              </li>
            );
          })}
        </ol>
      </Card>

      {!delivered && (
        <p className="rounded-lg bg-muslin px-3 py-2 text-xs text-ink-soft">
          To receive the package, the rider needs a 6-digit handover code. Ask the person who ordered it to share the code with you.
        </p>
      )}
      <p className="text-center text-xs text-ink-soft">
        This private link stops working <DateTimeDisplay value={tracking.link_expires_at} format="relative" />.
      </p>
    </div>
  );
}
