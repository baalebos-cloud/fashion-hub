import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { Card } from "@/components/ui/card";

type Side = { shown: number; clicked: number; converted: number; click_rate: number | null; conversion_rate: number | null };
type Verdict = { status: "collecting" | "learned_better" | "rules_better" | "no_difference"; message: string };
interface Health {
  mode: "rules" | "learned" | "experiment";
  experiment: string;
  report_days: number;
  data: { events_last_30_days: number; shoppers_last_30_days: number; related_pairs: number; related_items_built_at: string | null };
  surfaces: { surface: string; rules: Side; learned: Side; verdict: Verdict }[];
}

const SURFACE_LABEL: Record<string, string> = {
  budget_guide: "Budget guide", picked_for_you: "Picked for you", tailor_search: "Tailor search",
};
const MODE_LABEL: Record<Health["mode"], string> = {
  experiment: "Test running: each shopper sees either the fixed rules or learned ranking (50/50).",
  learned: "Learned ranking for everyone.",
  rules: "Fixed rules for everyone (learned ranking is off).",
};
const VERDICT_STYLE: Record<Verdict["status"], string> = {
  collecting: "bg-muslin text-ink-soft",
  no_difference: "bg-muslin text-ink",
  learned_better: "bg-success-wash text-success",
  rules_better: "bg-danger-wash text-thread",
};
const pct = (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

/** Admin: is learned ranking beating the fixed rules? Read-only. */
export function RecommendationsHealth() {
  const [data, setData] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    apiClient.get<Health>("/admin/recommendations/health").then((r) => setData(r.data))
      .catch(() => setError("Couldn't load recommendations health."));
  }, []);
  if (error) return <p role="alert" className="text-sm text-thread">{error}</p>;
  if (!data) return <p className="text-sm text-ink-soft">Checking recommendations…</p>;

  return (
    <section className="flex flex-col gap-4" aria-label="Recommendations health">
      <Card className="flex flex-col gap-2 p-4">
        <h2 className="font-display text-2xl text-ink">Recommendations health</h2>
        <p className="text-sm text-ink">{MODE_LABEL[data.mode]}</p>
        <p className="text-[13px] text-ink-soft">
          Last 30 days: {data.data.events_last_30_days.toLocaleString()} shopping actions from{" "}
          {data.data.shoppers_last_30_days.toLocaleString()} shoppers · {data.data.related_pairs.toLocaleString()} related-item pairs
          {data.data.related_items_built_at ? `, rebuilt ${new Date(data.data.related_items_built_at).toLocaleString()}` : ", not built yet"}.
          Change the ranking with the RECOMMENDATIONS_MODE setting (rules, learned or experiment).
        </p>
      </Card>
      {data.surfaces.map((s) => (
        <Card key={s.surface} className="flex flex-col gap-3 p-4">
          <h3 className="font-semibold text-ink">{SURFACE_LABEL[s.surface] ?? s.surface}</h3>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-ink-soft">
              <tr><th className="font-normal">Ranking</th><th className="font-normal">Lists shown</th>
                <th className="font-normal">Clicked</th><th className="font-normal">Added to cart or bought</th></tr>
            </thead>
            <tbody>
              {(["rules", "learned"] as const).map((side) => (
                <tr key={side} className="border-t border-line">
                  <td className="py-2">{side === "rules" ? "Fixed rules" : "Learned"}</td>
                  <td className="font-mono">{s[side].shown.toLocaleString()}</td>
                  <td className="font-mono">{pct(s[side].click_rate)}</td>
                  <td className="font-mono">{pct(s[side].conversion_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className={`rounded-control px-3 py-2 text-[13px] ${VERDICT_STYLE[s.verdict.status]}`}>{s.verdict.message}</p>
        </Card>
      ))}
      <p className="text-xs text-ink-soft">
        A list counts as clicked when the shopper opened one of its items from that list within a day, and as converted
        when they added one to cart or bought it within 7 days. A winner is only named once each side has 100 lists and
        the difference in clicks is unlikely to be chance.
      </p>
    </section>
  );
}
