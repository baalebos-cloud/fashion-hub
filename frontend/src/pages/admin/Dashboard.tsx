import { useEffect, useState } from "react";
import { dashboardApi, type CommerceSummary } from "@/api/dashboard.api";
import { Card } from "@/components/ui/card";
import type { DashboardSummaryCard } from "@/types/dashboard";

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);
  const [commerce, setCommerce] = useState<CommerceSummary | null>(null);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
    dashboardApi.getCommerceSummary().then(setCommerce).catch(() => setCommerce(null));
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-xl text-ink">Platform overview</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {summary.map((card) => (
          <Card key={card.label}>
            <div className="text-xs text-ink-soft">{card.label}</div>
            <div className="mt-1 text-xl font-medium text-ink">{card.value}</div>
          </Card>
        ))}
      </div>
      {commerce && (
        <section aria-label="Verified payments" className="rounded-xl border border-line p-4">
          <h2 className="mb-3 font-display text-lg text-ink">Verified commerce</h2>
          <div className="grid grid-cols-2 gap-4">
            <Card><p className="text-xs text-ink-soft">Verified payments</p><p className="text-xl">{commerce.verified_count}</p></Card>
            <Card><p className="text-xs text-ink-soft">Verified NGN payment volume</p><p className="text-xl">₦{Number(commerce.verified_volume_ngn).toLocaleString("en-NG")}</p></Card>
          </div>
          <p className="mt-3 text-xs text-ink-soft">{commerce.note}</p>
        </section>
      )}
    </div>
  );
}
