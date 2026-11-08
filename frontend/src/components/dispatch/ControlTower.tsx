import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { Card } from "@/components/ui/card";
import { describeFreshness } from "@/lib/utils/tracking";

interface Alert {
  type: string; severity: "critical" | "warning" | "info"; order_number: string | null; rider: string | null;
  minutes: number | null; message: string; action: string; delivery_id: string | null; request_id: string | null;
}
interface Performance {
  jobs_requested: number; delivered: number; median_minutes_to_assign: number | null;
  median_minutes_to_pickup: number | null; median_trip_minutes: number | null;
  auto_offer_acceptance: number | null; auto_offers_answered: number;
}
interface RiderRow {
  id: string; first_name: string; vehicle_type: string | null; rating: number;
  state: "online" | "offline" | "on_delivery"; active_jobs: number; tracking: { state: string; age_seconds: number | null } | null;
}

const LABEL: Record<string, string> = {
  unassigned_too_long: "No rider yet", pickup_delayed: "Late pickup", dropoff_delayed: "Late delivery",
  tracking_lost: "Tracking lost", location_off: "Location off", off_route: "Off route", rider_issue: "Rider issue",
};
const TONE = { critical: "border-thread/50 bg-thread/5", warning: "border-warning/40 bg-warning-wash", info: "border-line" };
const REFRESH_MS = 30_000;
type Tab = "attention" | "riders" | "today";

/** Top of the dispatch page: what needs a person now, who's out, and how today is going. */
export function ControlTower() {
  const [tab, setTab] = useState<Tab>("attention");
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [perf, setPerf] = useState<Performance | null>(null);
  const [riders, setRiders] = useState<RiderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [tower, team] = await Promise.all([
          apiClient.get<{ exceptions: Alert[]; performance: Performance }>("/admin/dispatch/control-tower"),
          apiClient.get<RiderRow[]>("/admin/dispatch/riders/overview"),
        ]);
        if (!active) return;
        setAlerts(tower.data.exceptions);
        setPerf(tower.data.performance);
        setRiders(team.data);
        setError(null);
      } catch {
        if (active) setError("Couldn't refresh the control tower. Showing the last update.");
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), REFRESH_MS);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const critical = alerts?.filter((a) => a.severity === "critical").length ?? 0;
  const tabs: [Tab, string][] = [
    ["attention", `Needs attention${alerts ? ` (${alerts.length})` : ""}`],
    ["riders", `Riders${riders ? ` (${riders.filter((r) => r.state !== "offline").length} out)` : ""}`],
    ["today", "Today"],
  ];

  return (
    <Card className="flex flex-col gap-3 p-4" role="region" aria-label="Control tower">
      <div className="flex flex-wrap gap-1" role="tablist">
        {tabs.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
            className={`min-h-11 rounded-full px-4 text-sm font-semibold ${tab === key ? "bg-indigo-wash text-indigo" : "text-ink-soft hover:text-ink"}`}>
            {label}{key === "attention" && critical > 0 && <span className="ml-1 rounded-full bg-thread px-1.5 text-xs text-paper">{critical}</span>}
          </button>
        ))}
      </div>
      {error && <p role="status" className="text-xs text-thread">{error}</p>}

      {tab === "attention" && (
        alerts === null ? <p className="text-sm text-ink-soft">Checking deliveries…</p>
          : alerts.length === 0 ? <p className="text-sm text-ink-soft">Nothing needs attention right now.</p>
            : <ul className="flex flex-col gap-2">
              {alerts.map((alert, index) => (
                <li key={`${alert.type}-${alert.delivery_id ?? alert.request_id}-${index}`}
                  className={`rounded-lg border px-3 py-2 text-sm ${TONE[alert.severity]}`}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium text-ink">
                      {LABEL[alert.type] ?? alert.type} · {alert.order_number ?? "order"}{alert.rider ? ` · ${alert.rider}` : ""}
                    </span>
                    <span className={`text-xs uppercase tracking-wide ${alert.severity === "critical" ? "text-thread" : "text-ink-soft"}`}>{alert.severity}</span>
                  </div>
                  <p className="text-ink">{alert.message}</p>
                  <p className="text-xs text-ink-soft">{alert.action}</p>
                </li>
              ))}
            </ul>
      )}

      {tab === "riders" && (
        riders === null ? <p className="text-sm text-ink-soft">Loading riders…</p>
          : riders.length === 0 ? <p className="text-sm text-ink-soft">No verified riders yet.</p>
            : <ul className="divide-y divide-line">
              {riders.map((rider) => (
                <li key={rider.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2 text-sm">
                  <span className="text-ink">{rider.first_name}
                    <span className="ml-1 text-xs text-ink-soft">{rider.vehicle_type ?? ""}{rider.rating > 0 ? ` · ★ ${rider.rating.toFixed(1)}` : ""}</span>
                  </span>
                  <span className="text-xs text-ink-soft">
                    {rider.state === "on_delivery" ? `On ${rider.active_jobs} deliver${rider.active_jobs === 1 ? "y" : "ies"}` : rider.state === "online" ? "Online, free" : "Offline"}
                    {rider.tracking && ` · ${describeFreshness(rider.tracking.state, rider.tracking.age_seconds).label}`}
                  </span>
                </li>
              ))}
            </ul>
      )}

      {tab === "today" && perf && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {([
            ["Jobs requested", perf.jobs_requested], ["Delivered", perf.delivered],
            ["Median time to find a rider", perf.median_minutes_to_assign != null ? `${perf.median_minutes_to_assign} min` : "—"],
            ["Median time to pickup", perf.median_minutes_to_pickup != null ? `${perf.median_minutes_to_pickup} min` : "—"],
            ["Median trip time", perf.median_trip_minutes != null ? `${perf.median_trip_minutes} min` : "—"],
            ["Automatic offers accepted", perf.auto_offer_acceptance != null ? `${Math.round(perf.auto_offer_acceptance * 100)}% of ${perf.auto_offers_answered}` : "—"],
          ] as [string, string | number][]).map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-ink-soft">{label}</dt>
              <dd className="font-display text-xl tabular-nums text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-xs text-ink-soft">Updates every 30 seconds. "Today" counts from midnight UTC.</p>
    </Card>
  );
}
