import { apiClient } from "@/lib/api/client";
import { useEffect, useState } from "react";
import { dashboardApi, type CommerceSummary } from "@/api/dashboard.api";
import { Card } from "@/components/ui/card";
import type { DashboardSummaryCard } from "@/types/dashboard";

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryCard[]>([]);
  const [commerce, setCommerce] = useState<CommerceSummary | null>(null);
  const [ops, setOps] = useState<{
    marketplace: Record<string, number>;
    verification: { kyc_pending: unknown[]; kyb_pending: unknown[] };
    financial_controls: { production_payments_enabled: boolean; ledger_balanced: boolean };
    delivery_issues: Array<{ id: string; type: string; status: string }>;
    audit_events: Array<{ id: string; action: string }>;
  } | null>(null);

  useEffect(() => {
    dashboardApi.getSummary().then(setSummary).catch(() => setSummary([]));
    apiClient.get("/admin/operations").then(r => setOps(r.data)).catch(() => setOps(null));
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
      {ops && (
        <section className="flex flex-col gap-4" aria-label="Admin operations">
          <h2 className="font-display text-lg">Marketplace operations</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {Object.entries(ops.marketplace).map(([role, count]) => (
              <Card key={role}><p className="text-xs capitalize">{role.replaceAll("_", " ")}</p><p className="text-xl">{count}</p></Card>
            ))}
          </div>
          <Card>
            <h3 className="font-medium">Verification queues</h3>
            <p>Pending NIN: {ops.verification.kyc_pending.length}</p>
            <p>Pending business checks: {ops.verification.kyb_pending.length}</p>
          </Card>
          <Card>
            <h3 className="font-medium">Financial controls</h3>
            <p>Production Saga payments: {ops.financial_controls.production_payments_enabled ? "Enabled" : "Disabled"}</p>
            <p>Ledger: {ops.financial_controls.ledger_balanced ? "Balanced" : "Needs investigation"}</p>
          </Card>
          <Card><h3 className="font-medium">Dispatch issues</h3>
            {ops.delivery_issues.map(x => <p key={x.id}>{x.type.replaceAll("_", " ")}: {x.status}</p>)}
          </Card>
          <Card><h3 className="font-medium">Audit events</h3>
            {ops.audit_events.map(x => <p key={x.id}>{x.action}</p>)}
          </Card>
        </section>
      )}
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
