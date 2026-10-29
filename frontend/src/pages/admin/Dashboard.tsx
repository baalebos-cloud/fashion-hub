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
    verification: { kyc_pending: Array<{id: string; user_id: string; documents: string[]}>; kyb_pending: Array<{id: string; owner_id: string; documents: string[]}> };
    financial_controls: { production_payments_enabled: boolean; ledger_balanced: boolean };
    delivery_issues: Array<{ id: string; type: string; status: string }>;
    audit_events: Array<{ id: string; action: string }>;
  } | null>(null);

  const [reviewError, setReviewError] = useState("");
  async function previewDocument(id: string) {
    try {
      const response = await apiClient.get<Blob>(`/admin/verification-documents/${id}/content`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const viewer = window.open(url, "_blank", "noopener,noreferrer");
      if (!viewer) {
        URL.revokeObjectURL(url);
        setReviewError("Allow pop-ups to preview this document.");
        return;
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
      setReviewError("");
    } catch {
      setReviewError("Unable to retrieve this private document preview.");
    }
  }

  async function review(kind: "kyc" | "kyb", id: string, approve: boolean) {
    const reason = approve ? null : window.prompt("Enter a reason for rejection");
    if (!approve && !reason?.trim()) return;
    try {
      await apiClient.post(`/admin/${kind}/${id}/review`, {approve, reason});
      const {data} = await apiClient.get("/admin/operations");
      setOps(data);
      setReviewError("");
    } catch {
      setReviewError("Review could not be completed. Check permissions and the verification record.");
    }
  }

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
            {reviewError && <p role="alert" className="text-thread">{reviewError}</p>}
            {ops.verification.kyc_pending.map(item => (
              <div key={item.id} className="flex flex-wrap gap-2 border-t border-line py-2 text-sm">
                <span>KYC {item.id.slice(0, 8)}</span>
                {item.documents.map(id => <button key={id} className="rounded border px-3 py-2" onClick={() => void previewDocument(id)}>Preview ID</button>)}
                <button className="rounded border px-3 py-2" onClick={() => void review("kyc", item.id, true)}>Approve</button>
                <button className="rounded border px-3 py-2" onClick={() => void review("kyc", item.id, false)}>Reject</button>
              </div>
            ))}
            {ops.verification.kyb_pending.map(item => (
              <div key={item.id} className="flex flex-wrap gap-2 border-t border-line py-2 text-sm">
                <span>KYB {item.id.slice(0, 8)}</span>
                {item.documents.map(id => <button key={id} className="rounded border px-3 py-2" onClick={() => void previewDocument(id)}>Preview certificate</button>)}
                <button className="rounded border px-3 py-2" onClick={() => void review("kyb", item.id, true)}>Approve</button>
                <button className="rounded border px-3 py-2" onClick={() => void review("kyb", item.id, false)}>Reject</button>
              </div>
            ))}
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
