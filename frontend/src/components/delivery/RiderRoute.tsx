import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "@/lib/api/client";
import { Card } from "@/components/ui/card";
import { deliveryRoutes } from "@/config/routes.config";
import { routeSummary, type PlannedRoute } from "@/lib/utils/planned-route";

/** The planned stop order across several deliveries. Shown for riders and, read-only, for dispatchers. */
export function RouteStops({ route, linkStops }: { route: PlannedRoute; linkStops: boolean }) {
  return (
    <ol className="flex flex-col gap-2">
      {route.stops.map((stop, index) => {
        const label = `${stop.kind === "pickup" ? "Collect" : "Deliver"} ${stop.order_number ?? "order"}`;
        const href = stop.delivery_id ? (stop.kind === "pickup" ? deliveryRoutes.pickup(stop.delivery_id) : deliveryRoutes.dropoff(stop.delivery_id)) : null;
        return (
          <li key={stop.key} className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0">
              <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-ink text-[11px] text-paper">{index + 1}</span>
              {linkStops && href ? <Link to={href} className="text-brass-deep underline">{label}</Link> : <span className="text-ink">{label}</span>}
            </span>
            <span className="shrink-0 text-xs tabular-nums text-ink-soft">~{stop.eta_minutes} min · {stop.load_after} on board</span>
          </li>
        );
      })}
    </ol>
  );
}

/** Rider dashboard card: "Your route" when they're carrying more than one order. */
export function RiderRoute() {
  const [route, setRoute] = useState<PlannedRoute | null>(null);
  useEffect(() => {
    let active = true;
    const load = () => apiClient.get<PlannedRoute | null>("/deliveries/mine/route")
      .then((r) => { if (active) setRoute(r.data); }).catch(() => undefined);
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  if (!route || route.stops.length === 0) return null;
  return (
    <Card className="flex flex-col gap-3 p-4" role="region" aria-label="Your route">
      <div>
        <h2 className="font-display text-lg text-ink">Your route</h2>
        <p className="text-xs text-ink-soft">{routeSummary(route)} Follow the stops in this order.</p>
      </div>
      <RouteStops route={route} linkStops />
    </Card>
  );
}
