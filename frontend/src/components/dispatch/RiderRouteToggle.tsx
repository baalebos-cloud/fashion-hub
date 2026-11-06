import { useState } from "react";
import { apiClient } from "@/lib/api/client";
import { RouteStops } from "@/components/delivery/RiderRoute";
import { routeSummary, type PlannedRoute } from "@/lib/utils/planned-route";

/** Dispatcher: a rider's planned multi-stop route, read-only. */
export function RiderRouteToggle({ partnerId }: { partnerId: string }) {
  const [open, setOpen] = useState(false);
  const [route, setRoute] = useState<PlannedRoute | null | undefined>(undefined);
  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) setRoute((await apiClient.get<PlannedRoute | null>(`/admin/dispatch/riders/${partnerId}/route`).catch(() => ({ data: null }))).data);
  }
  return (
    <div>
      <button type="button" onClick={() => void toggle()} aria-expanded={open} className="text-xs font-medium text-brass-deep underline">
        {open ? "Hide rider's route" : "Rider's route"}
      </button>
      {open && route === undefined && <p className="text-xs text-ink-soft">Loading…</p>}
      {open && route === null && <p className="text-xs text-ink-soft">This rider has a single delivery; no multi-stop route.</p>}
      {open && route && (
        <div className="mt-2 flex flex-col gap-1">
          <p className="text-xs text-ink-soft">{routeSummary(route)}</p>
          <RouteStops route={route} linkStops={false} />
        </div>
      )}
    </div>
  );
}
