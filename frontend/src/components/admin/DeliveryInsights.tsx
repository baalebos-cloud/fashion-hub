import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { Card } from "@/components/ui/card";

interface Recommendation { code: string; recommendation: string; evidence: Record<string, unknown>; confidence: string; reasoning: string; version: string }
interface Calibration { samples: number; factor: number | null; usable: boolean; reason: string | null;
  backtest?: { tested_on: number; mean_error_minutes_raw: number; mean_error_minutes_calibrated: number } }
interface Insights {
  readiness: { completed_deliveries: number; days_of_history: number; ready_for_models: boolean; message: string };
  eta_calibration: { enabled: boolean; by_vehicle: Record<string, Calibration> };
  riders: { partner_id: string; first_name: string; deliveries: number; median_minutes_to_pickup: number | null;
    median_trip_minutes: number | null; on_time_share: number | null; offer_acceptance: number | null }[];
  demand: { busiest_hours: { day: string; hour: number; average_jobs: number }[]; sample_requests: number; timezone: string };
  routes: { multistop_routes: number; planned_minutes_saved_total: number; median_actual_vs_estimated_trip: number | null; trips_measured: number };
  recommendations: Recommendation[];
  summary: { summary: string; source: string; version: string };
}

const pct = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);

/** Admin: what delivery history says, with evidence. Advisory only; nothing here changes deliveries. */
export function DeliveryInsights() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    apiClient.get<Insights>("/admin/dispatch/insights").then((r) => setData(r.data)).catch(() => setError("Couldn't load delivery insights."));
  }, []);
  if (error) return <p role="alert" className="text-sm text-thread">{error}</p>;
  if (!data) return <p className="text-sm text-ink-soft">Analysing delivery history…</p>;

  return (
    <section className="flex flex-col gap-4" aria-label="Delivery insights">
      <Card className="flex flex-col gap-2 p-4">
        <h2 className="font-display text-lg text-ink">Delivery insights</h2>
        <p className="text-sm text-ink">{data.summary.summary}</p>
        <p className="text-xs text-ink-soft">
          {data.summary.source === "rules" ? "Written from the numbers by fixed rules." : "Wording by AI from the same numbers."} {data.summary.version}
        </p>
        <p className={`rounded-lg px-3 py-2 text-xs ${data.readiness.ready_for_models ? "bg-muslin text-ink" : "bg-muslin text-ink-soft"}`}>
          {data.readiness.message}
        </p>
      </Card>

      <Card className="flex flex-col gap-2 p-4">
        <h3 className="text-sm font-medium text-ink">Suggestions</h3>
        {data.recommendations.length === 0 ? <p className="text-sm text-ink-soft">No suggestions right now.</p> : (
          <ul className="flex flex-col gap-2">
            {data.recommendations.map((rec) => (
              <li key={rec.code + rec.recommendation} className="rounded-lg border border-line p-3 text-sm">
                <p className="font-medium text-ink">{rec.recommendation}</p>
                <p className="text-xs text-ink-soft">{rec.reasoning}</p>
                <p className="mt-1 text-xs text-ink-soft">
                  Evidence: {Object.entries(rec.evidence).map(([k, v]) => `${k.replaceAll("_", " ")} ${String(v)}`).join(", ")} · confidence {rec.confidence}
                </p>
              </li>
            ))}
          </ul>
        )}
        <p className="text-xs text-ink-soft">Suggestions are advice. Nothing is changed automatically.</p>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="flex flex-col gap-2 p-4">
          <h3 className="text-sm font-medium text-ink">ETA accuracy by vehicle</h3>
          {Object.keys(data.eta_calibration.by_vehicle).length === 0 ? <p className="text-sm text-ink-soft">No finished deliveries to learn from yet.</p> : (
            <ul className="flex flex-col gap-1 text-sm">
              {Object.entries(data.eta_calibration.by_vehicle).map(([vehicle, c]) => (
                <li key={vehicle} className="text-ink">
                  <span className="capitalize">{vehicle}</span>: {c.factor ? `trips take ${c.factor}× the estimate` : c.reason}
                  {c.backtest && <span className="block text-xs text-ink-soft">
                    Tested on {c.backtest.tested_on} recent trips: average error {c.backtest.mean_error_minutes_raw} min raw vs {c.backtest.mean_error_minutes_calibrated} min calibrated.
                  </span>}
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-ink-soft">Calibration is {data.eta_calibration.enabled ? "switched on" : "off"} for live ETAs.</p>
        </Card>
        <Card className="flex flex-col gap-2 p-4">
          <h3 className="text-sm font-medium text-ink">Demand</h3>
          {data.demand.busiest_hours.length === 0 ? <p className="text-sm text-ink-soft">No demand pattern yet.</p> : (
            <ul className="text-sm text-ink">
              {data.demand.busiest_hours.map((h) => <li key={`${h.day}-${h.hour}`}>{h.day} {String(h.hour).padStart(2, "0")}:00 · about {h.average_jobs} jobs</li>)}
            </ul>
          )}
          <p className="text-xs text-ink-soft">4-week average per hour ({data.demand.timezone}), {data.demand.sample_requests} requests.
            {data.routes.multistop_routes > 0 && ` Multi-stop routes planned ${data.routes.planned_minutes_saved_total} min less than one-by-one.`}</p>
        </Card>
      </div>

      <Card className="p-4">
        <h3 className="mb-2 text-sm font-medium text-ink">Riders, last 30 days</h3>
        {data.riders.length === 0 ? <p className="text-sm text-ink-soft">No finished deliveries yet.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-ink-soft">
                <th className="py-1 pr-3 font-medium">Rider</th><th className="py-1 pr-3 font-medium">Deliveries</th>
                <th className="py-1 pr-3 font-medium">To pickup</th><th className="py-1 pr-3 font-medium">Trip</th>
                <th className="py-1 pr-3 font-medium">On time</th><th className="py-1 font-medium">Accepts offers</th>
              </tr></thead>
              <tbody>
                {data.riders.map((r) => (
                  <tr key={r.partner_id} className="border-t border-line tabular-nums">
                    <td className="py-1 pr-3">{r.first_name}</td><td className="py-1 pr-3">{r.deliveries}</td>
                    <td className="py-1 pr-3">{r.median_minutes_to_pickup ?? "—"} min</td><td className="py-1 pr-3">{r.median_trip_minutes ?? "—"} min</td>
                    <td className="py-1 pr-3">{pct(r.on_time_share)}</td><td className="py-1">{pct(r.offer_acceptance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </section>
  );
}
