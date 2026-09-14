import { useEffect, useState } from "react";
import { dashboardApi } from "@/api/dashboard.api";
import { Card } from "@/components/ui/card";
import type { DashboardSummaryCard } from "@/types/dashboard";

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
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
    </div>
  );
}
